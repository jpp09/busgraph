from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts" / "Teoria_dos_Grafos_no_BusGraph.docx"
OUTPUT.parent.mkdir(exist_ok=True)

NAVY = "17365D"
PALE_BLUE = "EAF2F8"
PALE_GRAY = "F5F6F7"
BORDER = "D9D9D9"
BLACK = RGBColor(0, 0, 0)


def set_cell_fill(cell, color):
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = tc_pr.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        tc_pr.append(shading)
    shading.set(qn("w:fill"), color)


def set_cell_margins(cell, top=110, start=120, bottom=110, end=120):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    margins = tc_pr.first_child_found_in("w:tcMar")
    if margins is None:
        margins = OxmlElement("w:tcMar")
        tc_pr.append(margins)
    for name, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = margins.find(qn(f"w:{name}"))
        if node is None:
            node = OxmlElement(f"w:{name}")
            margins.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_borders(table):
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = borders.find(qn(f"w:{edge}"))
        if tag is None:
            tag = OxmlElement(f"w:{edge}")
            borders.append(tag)
        tag.set(qn("w:val"), "single")
        tag.set(qn("w:sz"), "6")
        tag.set(qn("w:color"), BORDER)


def repeat_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def add_table(doc, headers, rows, widths=None):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_borders(table)
    repeat_header(table.rows[0])
    for i, header in enumerate(headers):
        cell = table.rows[0].cells[i]
        set_cell_fill(cell, NAVY)
        set_cell_margins(cell)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        run = cell.paragraphs[0].add_run(header)
        run.bold = True
        run.font.color.rgb = RGBColor(255, 255, 255)
        run.font.size = Pt(9.5)
        if widths:
            cell.width = widths[i]
    for row_index, values in enumerate(rows):
        cells = table.add_row().cells
        for i, value in enumerate(values):
            cell = cells[i]
            set_cell_margins(cell)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            if row_index % 2:
                set_cell_fill(cell, PALE_BLUE)
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(0)
            run = paragraph.add_run(str(value))
            run.font.size = Pt(9)
            if widths:
                cell.width = widths[i]
    doc.add_paragraph().paragraph_format.space_after = Pt(1)
    return table


def add_bullet(doc, text, level=0):
    style = "List Bullet" if level == 0 else "List Bullet 2"
    paragraph = doc.add_paragraph(style=style)
    paragraph.add_run(text)
    return paragraph


def add_code(doc, text):
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.left_indent = Cm(0.6)
    paragraph.paragraph_format.right_indent = Cm(0.6)
    paragraph.paragraph_format.space_before = Pt(4)
    paragraph.paragraph_format.space_after = Pt(8)
    p_pr = paragraph._p.get_or_add_pPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), PALE_GRAY)
    p_pr.append(shading)
    run = paragraph.add_run(text)
    run.font.name = "Consolas"
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), "Consolas")
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), "Consolas")
    run.font.size = Pt(9)


def add_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run("Página ")
    run.font.size = Pt(9)
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), "PAGE")
    paragraph._p.append(field)


doc = Document()
section = doc.sections[0]
section.page_width = Cm(21)
section.page_height = Cm(29.7)
section.top_margin = Cm(1.9)
section.bottom_margin = Cm(1.8)
section.left_margin = Cm(2.1)
section.right_margin = Cm(2.1)

styles = doc.styles
normal = styles["Normal"]
normal.font.name = "Arial"
normal._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
normal.font.size = Pt(10.5)
normal.font.color.rgb = BLACK
normal.paragraph_format.space_after = Pt(6)
normal.paragraph_format.line_spacing = 1.12

for style_name, size, before, after in (
    ("Title", 25, 0, 12),
    ("Subtitle", 12, 0, 18),
    ("Heading 1", 16, 16, 7),
    ("Heading 2", 12.5, 12, 5),
):
    style = styles[style_name]
    style.font.name = "Arial"
    style._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
    style._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
    style.font.size = Pt(size)
    style.font.color.rgb = BLACK
    style.font.bold = style_name != "Subtitle"
    style.paragraph_format.space_before = Pt(before)
    style.paragraph_format.space_after = Pt(after)

add_page_number(section.footer.paragraphs[0])

title = doc.add_paragraph(style="Title")
title.add_run("Teoria dos Grafos no Projeto BusGraph")
subtitle = doc.add_paragraph(style="Subtitle")
subtitle.add_run("Guia técnico e acadêmico sobre a modelagem da rede de ônibus e sua implementação")
date = doc.add_paragraph("Novembro de 2026")
date.alignment = WD_ALIGN_PARAGRAPH.LEFT
date.paragraph_format.space_after = Pt(20)

doc.add_heading("Objetivo do documento", level=1)
doc.add_paragraph(
    "Este documento explica onde a teoria dos grafos aparece no BusGraph, como a rede de ônibus é representada no código e como os algoritmos utilizam essa representação. A ideia central é tratar o sistema de transporte como uma rede: paradas e estados de viagem tornam-se vértices, enquanto deslocamentos e baldeações tornam-se arestas. Essa estrutura permite procurar caminhos e também estudar onde novas conexões podem melhorar a integração entre linhas."
)
doc.add_paragraph(
    "O projeto possui duas frentes relacionadas. O núcleo de rotas implementa um grafo direcionado e o algoritmo de Dijkstra. A interface atual compara duas linhas no mapa e procura locais próximos que podem virar novos pontos de conexão. Essa análise geográfica ainda não insere automaticamente os pontos no grafo; ela produz candidatos que podem ser avaliados e, depois, transformados em novos vértices e arestas."
)

doc.add_heading("Visão geral do fluxo", level=1)
flow = add_table(
    doc,
    ["Etapa", "Responsabilidade", "Resultado"],
    [
        ["1 Dados", "Ler paradas, linhas, sentidos, sequências e coordenadas da base EMDEC", "Registros normalizados"],
        ["2 Grafo", "Criar estados de parada e conexões direcionadas", "Lista de adjacência"],
        ["3 Algoritmo", "Calcular o caminho de menor custo", "Sequência de arestas"],
        ["4 Análise espacial", "Comparar trajetos e distâncias entre linhas", "Pontos de conexão candidatos"],
        ["5 Mapa", "Desenhar linhas, áreas candidatas e legenda", "Visualização para análise"],
    ],
    [Cm(2.4), Cm(8.3), Cm(5.0)],
)

doc.add_page_break()
doc.add_heading("Modelo de grafo usado no BusGraph", level=1)
doc.add_paragraph(
    "Um grafo pode ser escrito como G = (V, E), em que V é o conjunto de vértices e E é o conjunto de arestas. No BusGraph, o grafo é direcionado porque a ligação de uma parada A para uma parada B não garante a ligação inversa. Ele também é ponderado porque cada aresta possui um custo usado pelo algoritmo de caminho mínimo."
)

doc.add_heading("Vértices", level=2)
doc.add_paragraph(
    "O vértice representa um estado de viagem, e não somente uma localização física. Na construção local, o estado contém o identificador da parada, a linha e a ocorrência definida por sentido e sequência. Isso evita unir incorretamente visitas repetidas à mesma parada ou trechos de sentidos diferentes."
)
add_code(doc, "vértice = (parada_id, linha, (sentido, sequencia))")

doc.add_heading("Arestas", level=2)
add_table(
    doc,
    ["Tipo de aresta", "Origem e destino", "Uso no projeto"],
    [
        ["Viagem", "Paradas consecutivas da mesma linha", "Representa o avanço do ônibus no itinerário"],
        ["Transferência", "Estados de linhas diferentes na mesma parada", "Permite trocar de linha"],
        ["Ligação de terminal", "Plataformas próximas do mesmo terminal", "Representa uma conexão aproximada entre plataformas"],
        ["Conexão candidata", "Trecho próximo de outra linha ainda sem parada adequada", "Indica uma possível melhoria futura da rede"],
    ],
    [Cm(3.1), Cm(5.4), Cm(7.2)],
)

doc.add_heading("Pesos", level=2)
doc.add_paragraph(
    "O peso define o que significa uma rota melhor. A base local não contém tempos confiáveis entre paradas. Por isso, cada trecho recebe custo 1 no modo acadêmico, e o caminho mínimo representa a menor quantidade de trechos. Quando um arquivo com duração é usado, o mesmo modelo pode empregar minutos como peso. A interpretação do resultado depende sempre do peso escolhido."
)

doc.add_heading("Estrutura de armazenamento", level=2)
doc.add_paragraph(
    "A classe Graph usa uma lista de adjacência. Para cada vértice, o programa armazena somente as arestas que saem dele. Essa estrutura é adequada para redes de transporte, nas quais cada estado se conecta a poucos estados vizinhos em comparação com o número total de vértices."
)
add_code(doc, "graph.adjacency[origem] = [{target, weight, kind, line}, ...]")

doc.add_page_break()
doc.add_heading("Onde a matéria aparece no código", level=1)
add_table(
    doc,
    ["Arquivo", "Elemento de grafos", "Função no sistema"],
    [
        ["core/graph.py", "Grafo e lista de adjacência", "Define Graph e registra arestas direcionadas com peso e tipo"],
        ["services/graph_builder.py", "Construção de V e E", "Converte os trechos em vértices, arestas de viagem e transferências"],
        ["core/dijkstra.py", "Caminho mínimo", "Executa Dijkstra com múltiplas origens e destinos"],
        ["core/route_optimizer.py", "Interpretação do caminho", "Converte as arestas encontradas em linhas, trechos e baldeações"],
        ["data/local_loader.py", "Preparação da topologia", "Preserva linha, sentido e sequência para evitar ligações falsas"],
        ["services/connection_finder.py", "Candidatos a novos V e E", "Mede proximidade e sugere novos pontos de integração"],
        ["services/road_router.py", "Geometria do trajeto", "Ajusta a visualização às ruas com OSRM; não decide o caminho no grafo"],
        ["services/map_view.py", "Representação visual", "Desenha linhas, conexões e áreas candidatas no OpenStreetMap"],
        ["app.py", "Fluxo da aplicação", "Recebe as linhas escolhidas e coordena análise e mapa"],
    ],
    [Cm(4.0), Cm(4.1), Cm(7.6)],
)

doc.add_heading("Construção do grafo", level=2)
doc.add_paragraph(
    "A função build_graph percorre os trechos carregados. Para cada registro, ela cria um estado de origem e um estado de destino, depois adiciona uma aresta direcionada. Em seguida, agrupa os estados por parada e cria arestas de transferência entre linhas diferentes. Plataformas próximas com nome equivalente de terminal também podem ser ligadas."
)
add_code(doc, "graph.add_edge(source, target, custo, kind='ride', line=linha)")

doc.add_heading("Separação entre topologia e mapa", level=2)
doc.add_paragraph(
    "A linha desenhada no mapa não é o grafo em si. O grafo registra quais estados podem alcançar outros estados e qual é o custo dessa transição. O mapa apresenta coordenadas geográficas. O OSRM aproxima o desenho às ruas, mas não substitui os dados operacionais da linha nem altera automaticamente as arestas usadas pelo Dijkstra."
)

doc.add_page_break()
doc.add_heading("Como o algoritmo de Dijkstra funciona", level=1)
doc.add_paragraph(
    "Dijkstra encontra o caminho de menor custo quando os pesos são não negativos. O BusGraph aceita vários estados de origem e vários estados de destino porque uma parada física pode participar de diversas linhas. A fila de prioridade sempre retira primeiro o estado com menor custo conhecido."
)

steps = [
    "Inicializar o custo das origens com zero e inserir esses estados na fila de prioridade.",
    "Retirar da fila o estado com menor custo acumulado.",
    "Examinar cada aresta de saída e calcular o custo candidato até o vizinho.",
    "Atualizar o vizinho quando o novo custo for menor e guardar a aresta anterior.",
    "Parar ao alcançar um destino e reconstruir o caminho de trás para frente.",
]
for item in steps:
    add_bullet(doc, item)

doc.add_paragraph("O custo de um caminho P é a soma dos pesos de suas arestas:")
formula = doc.add_paragraph("custo(P) = soma dos pesos das arestas de P")
formula.alignment = WD_ALIGN_PARAGRAPH.CENTER
formula.runs[0].bold = True

doc.add_heading("Exemplo simplificado", level=2)
add_table(
    doc,
    ["Ligação", "Custo", "Interpretação"],
    [
        ["A para B pela linha 1", "1", "Um trecho percorrido"],
        ["B para C pela linha 1", "1", "Outro trecho percorrido"],
        ["B linha 1 para B linha 2", "0", "Transferência configurada sem tempo de espera"],
        ["C para D pela linha 2", "1", "Trecho após a transferência"],
    ],
    [Cm(6.2), Cm(2.2), Cm(7.3)],
)
doc.add_paragraph(
    "Se o caminho escolhido for A, B, C e D, o custo acadêmico será 3 porque somente as arestas de viagem recebem custo 1. Esse resultado significa três trechos, não três minutos. Para otimizar tempo real, seria necessário usar horários, espera e duração operacional como pesos."
)

doc.add_page_break()
doc.add_heading("Análise de possíveis novos pontos", level=1)
doc.add_paragraph(
    "A tela atual seleciona Linha 1 e Linha 2 e realiza uma análise espacial. Ela procura locais em que os itinerários passam próximos e distingue dois sentidos de melhoria: um novo ponto na Linha 1 que permita conexão com uma parada da Linha 2, e um novo ponto na Linha 2 que permita a conexão inversa. Os checkboxes controlam quais grupos aparecem no mapa."
)

add_table(
    doc,
    ["Regra atual", "Valor", "Finalidade"],
    [
        ["Paradas existentes próximas", "Até 150 m", "Localizar conexões que já podem existir"],
        ["Parada da outra linha perto do trajeto", "Até 200 m", "Criar uma sugestão de novo ponto"],
        ["Parada já existente na linha alvo", "Até 120 m", "Descartar uma sugestão desnecessária"],
        ["Sugestões muito próximas", "Até 250 m", "Agrupar candidatos repetidos"],
        ["Área desenhada no mapa", "Raio de 120 m", "Mostrar a região inicial para estudo"],
    ],
    [Cm(6.2), Cm(2.6), Cm(7.0)],
)

doc.add_heading("Relação com a teoria dos grafos", level=2)
doc.add_paragraph(
    "Uma sugestão geográfica só se torna uma melhoria da rede quando é incorporada à topologia. Um novo ponto de parada cria pelo menos um novo vértice em cada sentido ou ocorrência relevante. Os trechos vizinhos precisam ser divididos em novas arestas. Se o ponto permitir integração com outra linha, também deve existir uma aresta de transferência. Depois dessa alteração, o algoritmo pode comparar novamente os caminhos e medir se houve redução de trechos, baldeações ou outro custo escolhido."
)

doc.add_heading("Processo recomendado para avaliar uma melhoria", level=2)
for text in (
    "Gerar áreas candidatas pela proximidade dos trajetos.",
    "Validar calçadas, travessias, acessibilidade, sentido de operação e segurança.",
    "Escolher uma coordenada operacionalmente viável para a nova parada.",
    "Inserir o novo estado e suas arestas em uma cópia do grafo.",
    "Executar novamente as rotas de interesse e comparar os resultados antes e depois.",
):
    add_bullet(doc, text)

doc.add_page_break()
doc.add_heading("Limitações que afetam a interpretação", level=1)
add_bullet(doc, "A base local contém topologia e coordenadas, mas não fornece tempos confiáveis entre todas as paradas.")
add_bullet(doc, "A proximidade em linha reta não garante um caminho a pé curto ou seguro.")
add_bullet(doc, "O traçado do OSRM segue a malha viária e pode divergir do itinerário oficial do ônibus.")
add_bullet(doc, "Uma conexão próxima pode ocorrer em sentidos incompatíveis ou em horários diferentes.")
add_bullet(doc, "O custo zero de transferência não representa espera, caminhada ou perda de tempo operacional.")
add_bullet(doc, "As áreas candidatas são instrumentos de triagem e exigem validação de campo e dados operacionais.")

doc.add_heading("Como evoluir o trabalho acadêmico", level=1)
doc.add_paragraph(
    "O projeto já demonstra conceitos centrais da disciplina: grafos direcionados, pesos, lista de adjacência, caminho mínimo e transformação de um problema real em uma rede computacional. A próxima evolução pode comparar cenários. Para cada novo ponto candidato, o sistema cria uma versão alternativa do grafo, recalcula um conjunto fixo de viagens e registra as mudanças no número de trechos e baldeações. Com dados GTFS completos, também seria possível medir tempo estimado e serviços ativos por horário."
)

doc.add_heading("Síntese", level=1)
doc.add_paragraph(
    "A teoria dos grafos fornece o modelo que permite ao BusGraph representar e percorrer a rede de ônibus. A análise geográfica identifica oportunidades, enquanto o grafo permite testar o efeito dessas oportunidades sobre os caminhos possíveis. Manter essas duas funções separadas é importante: o mapa mostra onde uma melhoria pode existir; o grafo mostra como essa melhoria muda a conectividade e o custo das viagens."
)

doc.core_properties.title = "Teoria dos Grafos no Projeto BusGraph"
doc.core_properties.subject = "Explicação acadêmica e técnica do uso de grafos no BusGraph"
doc.core_properties.keywords = "BusGraph, teoria dos grafos, Dijkstra, transporte público"
doc.save(OUTPUT)
print(OUTPUT)
