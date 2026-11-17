# BusGraph — protótipo acadêmico

Aplicação em Python que carrega a base local EMDEC e compara duas linhas de ônibus para identificar possíveis pontos de conexão.

Ao abrir, o aplicativo carrega automaticamente a base em `datasets/emdec/consolidado`, sem download ou upload. Selecione Linha 1 e Linha 2; paradas das duas linhas a até 150 m em linha reta aparecem como possíveis conexões. A lista mostra os IDs e a distância entre elas. A proximidade não garante caminho a pé, acesso, operação no mesmo horário ou compatibilidade de sentido.

As ocorrências de parada por linha, sentido e sequência são preservadas para evitar atalhos entre visitas repetidas ou lacunas da coleta. A cobertura é parcial, sem horários de serviço ou caminhada entre paradas. Os carregadores CSV/GTFS permanecem no código, mas a interface usa somente a base local.

Plataformas com IDs diferentes, nome de terminal equivalente e distância de até 180 m são conectadas no grafo. No mapa, essa ligação aparece pontilhada em laranja; ela representa uma baldeação aproximada dentro do terminal, sem tempo de caminhada. Isso permite, por exemplo, partir de diferentes plataformas do Terminal BRT Campo Grande rumo ao Terminal Central.

## Executar
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Mapa interativo

O mapa OpenStreetMap aparece ao abrir o aplicativo. As duas linhas selecionadas aparecem em azul e vermelho, com trechos esquemáticos entre paradas. Cada marcador laranja representa um par de paradas próximas; clique nele para ver os IDs e a distância em linha reta. As ligações pontilhadas laranja mostram esses pares. O mapa requer internet, sem chave de API. Os créditos OpenStreetMap permanecem visíveis; o uso dos tiles segue https://operations.osmfoundation.org/policies/tiles/.

Dois controles permitem mostrar propostas de novos pontos em cada linha. Para sugerir um ponto na Linha 1, o sistema procura uma parada existente da Linha 2 a até 200 m do trajeto da Linha 1 e descarta a sugestão se a Linha 1 já possuir uma parada em até 120 m. O processo inverso gera propostas para a Linha 2. Sugestões a menos de 250 m entre si são agrupadas para evitar excesso de marcadores. As áreas azuis e vermelhas no mapa representam uma faixa inicial de análise, não uma localização definitiva para implantação.

## Carregadores adicionais no código

### CSV simplificado
Colunas obrigatórias:
- `origem`: identificador/nome da parada de origem
- `destino`: identificador/nome da parada seguinte
- `linha`: identificação da linha
- `duracao_min`: duração estimada do trecho em minutos

### GTFS ZIP
Necessita `stops.txt`, `routes.txt`, `trips.txt` e `stop_times.txt`.
O carregador calcula a média observada de duração de cada trecho consecutivo por linha, usando os horários do arquivo.

## Modelo de grafo
Cada vértice é um par `(parada, linha)`. Isso permite representar uma mesma parada servida por linhas diferentes como estados distintos. Arestas de viagem ligam paradas consecutivas da mesma linha; arestas de transferência conectam estados da mesma parada em linhas diferentes.

Dijkstra encontra o menor custo total com pesos não negativos.

## Limitações importantes
- Na interface, baldeações na mesma parada têm custo zero; não representam a espera real por um ônibus.
- A duração média por trecho não considera o horário específico de saída, trânsito em tempo real ou atrasos.
- A versão inicial não interpreta `calendar.txt`, `calendar_dates.txt`, `frequencies.txt`, `transfers.txt` nem acessibilidade.
- O CSV de exemplo é fictício e serve apenas para testar o funcionamento.
- Para uma pesquisa com horários reais de partida, será necessário evoluir para um algoritmo dependente do tempo e validar calendários/serviços ativos.

## Testes
```bash
python -m unittest discover -s tests -v
```

## Download automático do GTFS EMDEC
Na interface, selecione 'GTFS da EMDEC (automático)' e clique em 'Baixar dados da EMDEC'. O aplicativo utiliza o endpoint listado no README do projeto `paulo-raca/emdec-gtfs`: `https://emdec.paulo.costa.nom.br/route/all.gtfs`. O endpoint é externo e pode ficar indisponível; nesse caso, use upload manual.


## Fontes automáticas e contingência
O aplicativo tenta primeiro o endpoint `/route/all.gtfs` do projeto Emdec-GTFS. Se estiver indisponível, tenta baixar o ZIP do repositório GitHub e localizar os arquivos GTFS na pasta interna `gtfs/`. A estrutura do repositório pode mudar; nesse caso, use o upload manual.
