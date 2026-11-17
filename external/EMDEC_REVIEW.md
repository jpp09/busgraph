# Revisão local do emdec-gtfs

Data: 2026-11-16. Origem: https://github.com/paulo-raca/emdec-gtfs
Commit: 04b07f91e1c77adab66ea8a695384bd21079a202 (2020-04-14).

## Segurança e dependências

- Revisados os módulos Python e configurações da aplicação. Não foi identificado comportamento malicioso evidente; isso não é certificação de ausência de malware.
- Varredura personalizada do Windows Defender executada na pasta clonada. A consulta posterior não retornou detecções para essa pasta.
- Nenhuma dependência instalada. Não foram auditados os pacotes transitivos ou os dois forks externos.
- requirements.txt não fixa versões. Inclui quart, aiohttp, lxml, cssselect, google-cloud-ndb, unicodecsv, geopy, aiosqlite, asyncio-pool e forks Git de euclid e aiocache sem commit fixo.
- app.yaml indica Python 3.7; o Python local é 3.15.2. Compatibilidade não foi validada.
- geocode.py lê geocode_keys.txt e imprime as chaves no console. Não fornecer credenciais antes de corrigir isso.
- Coleta utiliza HTTP e não verifica status HTTP; cache local SQLite; saída JSON em out/. Google Geocoding é opcional e pode ser desativado sem chaves.

## Teste da fonte e extração

GET http://www.emdec.com.br/ABusInf/consultarlinha.asp: HTTP 404.
GET https://www.emdec.com.br/ABusInf/consultarlinha.asp: HTTP 404.
Respostas preservadas em emdec-gtfs-probe-http.html e emdec-gtfs-probe.html.
check_emdec_probe.py executa somente as funções revisadas de listagem do código original sobre essas respostas, sem importar dependências ou acessar credenciais.

A execução completa está bloqueada pela fonte inexistente. Não foi gerado dataset real. É necessário localizar a fonte atual e adaptar o coletor antes de instalar e executar a aplicação completa.

Outro ponto para futura integração: emdec2gtfs.py preenche horários apenas na primeira e última parada; o carregador atual do BusGraph exige horários em trechos consecutivos. Será necessário tratar os horários intermediários explicitamente como estimativas.
