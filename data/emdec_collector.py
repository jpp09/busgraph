"""Coletor do portal público atual da EMDEC, sem executar JavaScript remoto."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import time
import unicodedata
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = 'https://portal.emdec.com.br'


def clean_text(value):
    return ' '.join(unicodedata.normalize('NFC', str(value or '')).split())


def parse_geojson(text):
    match = re.fullmatch(r'\s*var\s+geoJSONPtoItinerariosPontos\s*=\s*(.*?)\s*;?\s*', text, re.S)
    if not match:
        raise ValueError('Formato do arquivo de paradas mudou.')
    payload = json.loads(match.group(1))
    if payload.get('type') != 'FeatureCollection':
        raise ValueError('GeoJSON inválido.')
    return payload


def normalize(route, payload):
    stops, issues, seen = [], [], set()
    code = clean_text(route['numero_linha'])
    for index, feature in enumerate(payload['features']):
        try:
            props = feature['properties']
            if clean_text(props['num_linha']) != code:
                raise ValueError('linha divergente')
            geometry = feature['geometry']
            if geometry['type'] != 'Point':
                raise ValueError('geometria não é Point')
            lon, lat = map(float, geometry['coordinates'])
            if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
                raise ValueError('coordenadas inválidas')
            direction = str(props['sentido'])
            sequence = float(props['ptseqlinha'])
            stop_id = clean_text(props['ponto_id'])
            if direction not in ('1', '2') or not stop_id or not math.isfinite(sequence) or sequence < 1:
                raise ValueError('identificador, sentido ou sequência inválidos')
            row = dict(linha=code, nome_linha=clean_text(route['nome']),
                       nome_linha_mapa=clean_text(props.get('nome_linha')),
                       sentido=direction, sequencia=sequence, parada_id=stop_id,
                       logradouro=clean_text(props.get('ende_logradouro')),
                       numero=clean_text(props.get('ende_numero')), latitude=lat, longitude=lon,
                       status=clean_text(props.get('status')), tipo_uso=clean_text(props.get('tipo_uso')))
            signature = json.dumps(row, sort_keys=True)
            if signature in seen:
                issues.append({'registro': index, 'motivo': 'duplicata exata removida'})
                continue
            seen.add(signature)
            stops.append(row)
        except (KeyError, TypeError, ValueError) as exc:
            issues.append({'registro': index, 'motivo': str(exc)})
    stops.sort(key=lambda s: (s['sentido'], s['sequencia']))
    names = sorted({s['nome_linha_mapa'] for s in stops if s['nome_linha_mapa'] != clean_text(route['nome'])})
    if names:
        issues.append({'motivo': 'nome do mapa diverge da consulta', 'nomes_mapa': names})
    counts = Counter((s['sentido'], s['sequencia']) for s in stops)
    conflicts = [list(key) for key, count in counts.items() if count > 1]
    if conflicts:
        issues.append({'motivo': 'sequências conflitantes; registros preservados', 'sequencias': conflicts})
    # Nunca unir através de uma sequência ausente ou ambígua.
    edges = []
    for a, b in zip(stops, stops[1:]):
        if (a['sentido'] == b['sentido'] and 0 < b['sequencia'] - a['sequencia'] <= 1
                and counts[(a['sentido'], a['sequencia'])] == counts[(b['sentido'], b['sequencia'])] == 1):
            edges.append(dict(origem=a['parada_id'], destino=b['parada_id'], linha=code,
                              sentido=a['sentido'], sequencia=a['sequencia'], duracao_min=None))
    return {'linha': route, 'paradas': stops, 'trechos': edges, 'avisos': issues}


def fetch(path, form=None):
    request = Request(BASE + path, data=urlencode(form).encode() if form else None,
                      headers={'User-Agent': 'BusGraph-Academic-Collector/1.0'})
    with urlopen(request, timeout=30) as response:
        return response.read().decode('utf-8-sig')


def collect(code, output, offline=None):
    if not re.fullmatch(r'[A-Za-z0-9-]+', code):
        raise ValueError('Código de linha inválido.')
    target = output / code
    target.mkdir(parents=True, exist_ok=True)
    if offline:
        search = (offline / f'emdec-search-{code}.json').read_text(encoding='utf-8')
        raw = (offline / f'emdec-stops-{code}.js').read_text(encoding='utf-8')
    else:
        search = fetch('/consultalinha/consulta_linha.php', {'term': code})
        time.sleep(1)
        raw = fetch(f'/itinerarios/js/pto_itinerarios_pontos-{code}.js')
    (target / 'consulta.raw.json').write_text(search, encoding='utf-8')
    (target / 'paradas.raw.js').write_text(raw, encoding='utf-8')
    matches = [json.loads(item['text']) for item in json.loads(search)]
    matches = [r for r in matches if clean_text(r['numero_linha']) == code]
    if len(matches) != 1:
        raise ValueError(f'Esperada uma correspondência exata para {code}; encontradas {len(matches)}.')
    result = normalize(matches[0], parse_geojson(raw))
    if not result['paradas']:
        raise ValueError('Nenhuma parada válida encontrada.')
    result['proveniencia'] = {'processado_em': datetime.now(timezone.utc).isoformat(),
                             'modo': 'captura_local' if offline else 'online',
                             'consulta_url': BASE + '/consultalinha/consulta_linha.php',
                             'mapa_url': BASE + f'/itinerarios/js/pto_itinerarios_pontos-{code}.js',
                             'tempos': 'não fornecidos; duracao_min permanece nula'}
    (target / 'dados.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('linhas', nargs='+')
    parser.add_argument('--output', type=Path, default=Path('datasets/emdec'))
    parser.add_argument('--offline', type=Path, help='Pasta das capturas anteriores, para reprodução sem rede.')
    args = parser.parse_args()
    for index, code in enumerate(dict.fromkeys(args.linhas)):
        if index and not args.offline:
            time.sleep(1)
        result = collect(code, args.output, args.offline)
        print(f"{code}: {len(result['paradas'])} paradas, {len(result['trechos'])} trechos, {len(result['avisos'])} avisos")


if __name__ == '__main__':
    main()
