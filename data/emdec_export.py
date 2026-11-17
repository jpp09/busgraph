"""Descobre linhas numéricas do portal e consolida paradas/trechos em CSV."""
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from urllib.parse import quote

from data.emdec_collector import BASE, clean_text, fetch, normalize, parse_geojson


def write_csv(path, rows, fields):
    with path.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    root = Path('datasets/emdec/consolidado')
    root.mkdir(parents=True, exist_ok=True)
    routes = {}
    # Toda identificação numérica contém ao menos um destes caracteres.
    # Preservamos todas as variantes retornadas, sem adivinhar códigos de linha.
    for digit in '0123456789':
        response = fetch('/consultalinha/consulta_linha.php', {'term': digit})
        (root / f'busca-{digit}.json').write_text(response, encoding='utf-8')
        for item in json.loads(response):
            route = json.loads(item['text'])
            routes[route['linhaosletra']] = route
        print(f'Busca {digit}: {len(routes)} variantes acumuladas', flush=True)
        time.sleep(1)
    (root / 'linhas.json').write_text(json.dumps(list(routes.values()), ensure_ascii=False, indent=2), encoding='utf-8')
    # Mapas são publicados por número de linha, e não por variante administrativa.
    by_code = {}
    for route in routes.values():
        by_code.setdefault(clean_text(route['numero_linha']), []).append(route)
    stops, edges, failures, warnings = [], [], [], []
    raw_dir = root / 'originais'
    raw_dir.mkdir(exist_ok=True)
    for index, (code, variants) in enumerate(sorted(by_code.items()), 1):
        try:
            path = f'/itinerarios/js/pto_itinerarios_pontos-{quote(code, safe="")}.js'
            raw = fetch(path)
            # Use an index for filesystem names; remote identifiers are untrusted.
            (raw_dir / f'{index:04d}.js').write_text(raw, encoding='utf-8')
            result = normalize(variants[0], parse_geojson(raw))
            if not result['paradas']:
                raise ValueError('Nenhuma parada válida')
            if len(variants) > 1:
                result['avisos'].append({'motivo': 'múltiplas variantes na consulta', 'variantes': variants})
            stops.extend(result['paradas'])
            edges.extend(result['trechos'])
            warnings.append({'linha': code, 'origem': BASE + path,
                             'arquivo_original': f'originais/{index:04d}.js', 'avisos': result['avisos']})
            print(f'{index}/{len(by_code)} {code}: {len(result["paradas"])} paradas', flush=True)
        except Exception as exc:
            failures.append({'linha': code, 'erro': str(exc)})
            print(f'{index}/{len(by_code)} {code}: FALHA {exc}', flush=True)
        time.sleep(1)
    write_csv(root / 'paradas.csv', stops, ['linha', 'nome_linha', 'nome_linha_mapa', 'sentido',
              'sequencia', 'parada_id', 'logradouro', 'numero', 'latitude', 'longitude', 'status', 'tipo_uso'])
    write_csv(root / 'trechos.csv', edges, ['origem', 'destino', 'linha', 'sentido', 'sequencia', 'duracao_min'])
    report = {'coletado_em': datetime.now(timezone.utc).isoformat(), 'linhas_descobertas': len(by_code),
              'linhas_coletadas': len(warnings), 'registros_paradas': len(stops), 'trechos': len(edges),
              'falhas': failures, 'revisao': warnings,
              'limites': 'Linhas retornadas pela busca por dígitos; cobertura total da rede não garantida. Tempos ausentes.'}
    (root / 'relatorio.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'revisao'}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
