# Coleta EMDEC

Coletor independente do projeto legado, apenas com biblioteca padrão do Python:

```powershell
python -m data.emdec_collector 332
python -m data.emdec_collector 332 333 --output datasets/emdec
```

Para reproduzir a captura inicial sem rede:

```powershell
python -m data.emdec_collector 332 --offline external
```

Cada linha gera `consulta.raw.json`, `paradas.raw.js` (originais, não executados)
e `dados.json` (paradas normalizadas, trechos, avisos e proveniência).
Uma nova execução substitui os arquivos daquela linha; use `--output` para guardar snapshots.

A limpeza normaliza Unicode e espaços, valida coordenadas, separa sentidos,
ordena pela sequência original (incluindo frações) e remove apenas duplicatas exatas.
Visitas repetidas à mesma parada são preservadas. O nome da consulta é usado como
nome principal, mantendo o nome do mapa para auditoria. Conflitos de sequência
são preservados e não geram conexões; saltos maiores que 1 também não são unidos.

O coletor consulta somente os códigos informados, com timeout e intervalo entre
requisições. Não instala dependências antigas, executa JavaScript ou usa chaves.

Os tempos entre paradas não estão disponíveis nesta fonte: `duracao_min` é nulo.
Este JSON é uma base de topologia, ainda não uma entrada pronta para o otimizador
de tempo do aplicativo. Não converta esses valores para zero. Horários de partida
do portal ainda não são coletados por este módulo.

Testes: `python -m unittest discover -s tests -v`.

## CSV consolidado

```powershell
python -m data.emdec_export
```

Descobre os códigos retornados pela consulta por dígitos e baixa os mapas
sequencialmente, com intervalo de um segundo. Saída em `datasets/emdec/consolidado`:

- `paradas.csv`: uma ocorrência de parada por linha, sentido e sequência.
- `trechos.csv`: conexões não ambíguas; duração vazia, sem estimativas inventadas.
- `relatorio.json`: cobertura observada, falhas e inconsistências por linha.
- `linhas.json`, buscas e `originais/`: respostas para auditoria.

Os CSVs usam vírgula como separador e UTF-8 com BOM. IDs devem ser importados
como texto. Repetições de uma parada em diferentes linhas/sentidos são intencionais.
Não é garantido que a busca pública exponha todas as linhas existentes.
