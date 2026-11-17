# BusGraph Campinas

Aplicação em Python e Streamlit para comparar os trajetos de ida de duas linhas da EMDEC, calcular distâncias viárias entre paradas e sugerir uma distribuição de pontos a cada 300 metros.

## Funcionalidades

- Seleção de duas linhas da base local da EMDEC.
- Exibição dos trajetos de ida em azul e vermelho.
- Setas indicando o sentido de cada rota.
- Distâncias calculadas sobre as ruas com o OSRM.
- Pesos por aresta e distância acumulada.
- Proposta de pontos distribuídos a cada 300 m.
- Exportação dos resultados em CSV.
- Geração de um executável único para Windows.

## Requisitos

- Windows 10 ou 11, preferencialmente 64 bits.
- Uma versão estável do Python para Windows, também 64 bits.
- Acesso à internet durante a instalação e durante o uso do mapa.
- Git é necessário somente para clonar o repositório.

Evite versões preview ou experimentais do Python, pois o PyInstaller e algumas dependências podem ainda não oferecer suporte a elas.

## Estrutura essencial

```text
busgraph/
├── app.py
├── build_exe.py
├── launcher.py
├── requirements.txt
├── requirements-build.txt
├── data/
│   └── local_loader.py
├── services/
│   ├── ida_view.py
│   ├── road_router.py
│   └── weighted_routes.py
└── datasets/emdec/consolidado/
    ├── paradas.csv
    ├── relatorio.json
    └── trechos.csv
```

Os três arquivos de `datasets/emdec/consolidado/` são obrigatórios. Eles são incluídos automaticamente no executável.

## Preparar o projeto

Abra o PowerShell na pasta em que deseja manter o projeto.

### 1. Clonar e entrar na pasta

```powershell
git clone https://github.com/jpp09/busgraph.git
cd busgraph
```

Se o projeto já estiver no computador, apenas abra o PowerShell na pasta `busgraph`.

### 2. Criar um ambiente virtual

```powershell
python -m venv .venv
```

### 3. Ativar o ambiente

```powershell
.\.venv\Scripts\Activate.ps1
```

Se o PowerShell bloquear a ativação, libere-a somente para a sessão atual:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 4. Atualizar o instalador de pacotes

```powershell
python -m pip install --upgrade pip
```

## Executar durante o desenvolvimento

Instale apenas as dependências da aplicação:

```powershell
python -m pip install -r requirements.txt
```

Inicie o Streamlit:

```powershell
python -m streamlit run app.py
```

O navegador deverá abrir em `http://localhost:8501`.

## Gerar o executável do Windows

O `.exe` precisa ser gerado no Windows. Um build feito no Linux ou no macOS não produz um executável nativo do Windows.

### 1. Instalar as dependências de build

Com o ambiente virtual ativado, execute:

```powershell
python -m pip install -r requirements-build.txt
```

Esse arquivo instala as dependências da aplicação e o PyInstaller.

### 2. Validar a aplicação antes do build

```powershell
python -m streamlit run app.py
```

Selecione duas linhas e confirme que o mapa, as rotas e as setas aparecem. Encerre com `Ctrl+C` no PowerShell.

### 3. Gerar o `.exe`

```powershell
python build_exe.py
```

O script executa o PyInstaller no modo `onefile`, inclui a base consolidada e gera:

```text
dist/BusGraph.exe
```

As pastas `build/`, `dist/` e o arquivo temporário `.spec` não são versionados pelo Git.

## Abrir o executável

Execute:

```powershell
.\dist\BusGraph.exe
```

Uma janela de console será aberta para manter o servidor local em execução. O BusGraph procura uma porta livre a partir de `8501` e abre no navegador somente quando o servidor estiver pronto. Não feche essa janela enquanto estiver usando o BusGraph. Para encerrar, volte ao console e pressione `Ctrl+C` ou feche a janela.

Na primeira abertura, o Windows pode demorar alguns segundos para descompactar o executável em uma pasta temporária.

## Distribuir o aplicativo

O arquivo `dist/BusGraph.exe` já contém:

- A aplicação Streamlit.
- Os módulos do BusGraph.
- As dependências Python necessárias.
- A base consolidada usada pela interface.

Em condições normais, basta copiar somente `BusGraph.exe` para outro computador Windows de mesma arquitetura. A máquina de destino não precisa ter Python instalado, mas precisa de internet para carregar o OpenStreetMap e consultar o OSRM.

## Gerar novamente após alterações

Salve as mudanças e execute novamente:

```powershell
python build_exe.py
```

O script usa as opções `--clean` e `--noconfirm`, portanto substitui o build anterior automaticamente.

## Problemas comuns

### `python` não é reconhecido

Instale o Python para Windows e marque a opção de adicioná-lo ao `PATH`. Depois feche e abra novamente o PowerShell.

### `PyInstaller não encontrado`

Ative o ambiente virtual e instale as dependências de build:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-build.txt
```

### O PowerShell não permite ativar o ambiente

Use:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Essa configuração vale somente para a janela atual.

### O executável abre, mas o mapa não mostra as rotas

Verifique a conexão com a internet. O mapa usa tiles do OpenStreetMap, e as geometrias viárias são consultadas no OSRM.

### A porta 8501 já está em uso

O launcher procura automaticamente outra porta livre até `8520`. O endereço correto é mostrado na janela do console.

### O Windows exibe um alerta ao abrir o `.exe`

O executável é gerado localmente e não possui assinatura digital. Confirme que ele foi criado a partir deste código antes de permitir a execução.

## Limitações

- O OSRM fornece uma estimativa viária e não um itinerário oficial homologado pela EMDEC.
- Trechos sem resposta viária válida são omitidos; o aplicativo não cria ligações retas como substituição.
- Os pontos sugeridos precisam de validação de segurança, acessibilidade e operação em campo.
- A disponibilidade do mapa e das rotas depende dos serviços externos.
