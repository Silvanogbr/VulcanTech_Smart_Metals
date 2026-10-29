# VulcanTech Smart Metals S.A.

Projeto integrador demonstrativo de análise de sensores industriais, manutenção preditiva e inspeção visual de soldas. O sistema usa o CSV fornecido, treina modelos de classificação e disponibiliza um site local com páginas separadas para consultar os dados.

> **Escopo:** os dados e as imagens de teste são demonstrativos. O sistema não controla máquinas, não envia comandos a CLPs e não substitui inspeção ou validação industrial.

## Índice

- [Objetivos](#objetivos)
- [O que o projeto faz](#o-que-o-projeto-faz)
- [Dados de entrada](#dados-de-entrada)
- [Instalação e execução no Windows](#instalação-e-execução-no-windows)
- [Notebook de tratamento](#notebook-de-tratamento)
- [Páginas do site](#páginas-do-site)
- [API](#api)
- [Pipeline de dados](#pipeline-de-dados)
- [Modelos e resultados](#modelos-e-resultados)
- [Inspeção visual](#inspeção-visual)
- [Docker](#docker)
- [Estrutura dos arquivos](#estrutura-dos-arquivos)
- [Parecer técnico e limitações](#parecer-técnico-e-limitações)

## Objetivos

O projeto reúne as etapas pedidas no enunciado:

1. Limpar leituras de sensores, quantificar dados ausentes e criar variáveis derivadas.
2. Comparar classificadores para as quatro classes de `tipo_falha` e medir o recall no trecho temporal de teste.
3. Disponibilizar uma API para receber leituras e imagens.
4. Criar um site simples para explorar sensores, resultados do modelo e uma demonstração de inspeção visual.

## O que o projeto faz

- **Visão geral:** filtros por célula, liga e período; quantidade de registros; percentual de falhas; gráficos por classe/célula; médias por liga; avaliação do modelo.
- **Sensores:** série temporal por variável e célula, faixa de referência, resumo e download dos registros filtrados em CSV.
- **Inspeção de solda:** envio de uma imagem JPG ou PNG, seleção opcional da região do cordão, mapa falso-colorido de contraste/textura e triagem heurística.
- **API:** inferência tabular em `/predict`, análise de imagem em `/inspect/weld` e documentação interativa em `/docs`.

O site foi escrito em HTML, CSS e JavaScript e é servido pelo FastAPI. Não requer Streamlit nem um processo Node.js.

## Dados de entrada

O arquivo usado é `dados_sensores_vulcantech.csv`. Ele contém 10.000 registros, com amostras em intervalos de cinco minutos, quatro células, três ligas, sete sensores numéricos e a classe de falha.

| Coluna | Significado |
|---|---|
| `timestamp` | Data e hora da amostra |
| `id_celula` | Identificador `CEL-201` a `CEL-204` |
| `liga_metalica` | Aço carbono, alumínio ou titânio |
| `temperatura_fuso_c` | Temperatura do fuso/matriz, °C |
| `vibracao_triaxial_rms_mms` | Vibração RMS, mm/s |
| `torque_fuso_nm` | Torque do fuso, Nm |
| `vazao_refrigerante_lmin` | Vazão do fluido, L/min |
| `corrente_estator_amp` | Corrente do motor, A |
| `pressao_hidraulica_bar` | Pressão, bar |
| `nivel_ruido_db` | Nível de ruído, dB |
| `tipo_falha` | Classe alvo, de 0 a 3 |

Classes de `tipo_falha`:

| Código | Significado |
|---:|---|
| 0 | Operação normal |
| 1 | Desgaste de ferramenta/fuso |
| 2 | Falha de refrigeração/sobreaquecimento |
| 3 | Desalinhamento ou trinca |

No arquivo atual, as classes estão desbalanceadas: 8.557 registros normais, 470 de classe 1, 509 de classe 2 e 464 de classe 3. Há 1% de valores ausentes entre as leituras dos sensores, além de valores sentinela fora das faixas operacionais.

## Instalação e execução no Windows

Abra o PowerShell na pasta do projeto. Python 3.10 ou superior é necessário.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Notebook de tratamento

Abra [`notebooks/01_tratamento_dados.ipynb`](notebooks/01_tratamento_dados.ipynb) no VS Code, selecione o kernel Python do ambiente `.venv` e use **Run All / Executar tudo**. O notebook apresenta cada etapa e grava `sensores_preparados.csv` e `ausencias_por_celula_liga.csv` em `dados_processados/`.

Para instalar também o kernel usado pelo notebook, use o arquivo de dependências de desenvolvimento:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-notebook.txt
```

Depois, treine e compare os modelos:

```powershell
.\.venv\Scripts\python.exe src/treinar_modelo.py
```

Se quiser repetir o tratamento sem abrir o notebook, execute no PowerShell:

```powershell
.\.venv\Scripts\python.exe src/pipeline.py
```

Inicie o site e a API:

```powershell
.\.venv\Scripts\uvicorn.exe api:app --app-dir src --reload
```

Abra estas páginas no navegador:

- Capa: <http://127.0.0.1:8000/>
- Visão geral: <http://127.0.0.1:8000/dashboard>
- Sensores: <http://127.0.0.1:8000/sensors>
- Inspeção visual: <http://127.0.0.1:8000/inspection>
- Documentação Swagger: <http://127.0.0.1:8000/docs>

Para encerrar o servidor, volte ao terminal e pressione `Ctrl+C`. Se a porta 8000 estiver ocupada, inicie com `--port 8001` e acesse a mesma rota na nova porta.

### Arquivos criados na execução

- `dados_processados/sensores_preparados.csv`: dados limpos e atributos derivados.
- `dados_processados/ausencias_por_celula_liga.csv`: percentual ausente por célula e liga, antes da limpeza.
- `modelos/modelo_falhas.joblib`: modelo selecionado para inferência.
- `modelos/relatorio_modelo.json`: recall, matriz de confusão e atributos importantes usados no site.

As pastas `dados_processados/` e `modelos/` são geradas localmente e estão listadas no `.gitignore`.

## Páginas do site

### Capa

Página inicial com uma ilustração vetorial de soldagem e botões para as áreas do projeto.

### Visão geral

Os filtros alteram os indicadores, os gráficos e a tabela por liga. O painel de modelo apresenta as métricas salvas pelo último treino. O indicador de OEE real fica indisponível porque o CSV não contém dados de disponibilidade, desempenho e qualidade da produção.

### Sensores

Permite selecionar célula, liga, variável e período. O gráfico mostra os valores no tempo e a faixa operacional indicada no enunciado. O botão de download exporta as linhas filtradas.

### Inspeção de solda

Selecione uma imagem JPG ou PNG. Depois, arraste sobre ela para marcar a região a analisar; se não marcar uma área, a imagem inteira será usada. O resultado apresenta a imagem com regiões de contraste destacadas, contornos candidatos e uma indicação preliminar:

- **Revisar a solda:** foram encontrados vários contornos arredondados ou a área estimada ultrapassou o limite inicial.
- **Sem alerta visual pelo filtro:** o filtro não encontrou esses sinais em quantidade elevada.
- **Imagem inconclusiva:** área selecionada pequena ou foto sem nitidez suficiente.

As imagens em `assets/amostras_visao/` podem ser usadas para experimentar a tela. Elas são sintéticas, criadas pelo script `scripts/gerar_amostras_visao.py`.

## API

### `POST /predict`

Recebe uma leitura JSON e devolve a classe prevista e a confiança estimada pelo modelo. A rota `/docs` oferece um exemplo válido. Os valores categóricos aceitos são:

- `id_celula`: `CEL-201`, `CEL-202`, `CEL-203` ou `CEL-204`.
- `liga_metalica`: `Aco_Carbono_316L`, `Aluminio_7075` ou `Liga_Titanio_Ti6Al4V`.

Exemplo de corpo:

```json
{
  "id_celula": "CEL-201",
  "liga_metalica": "Aco_Carbono_316L",
  "temperatura_fuso_c": 56.0,
  "vibracao_triaxial_rms_mms": 1.9,
  "torque_fuso_nm": 100.0,
  "vazao_refrigerante_lmin": 29.0,
  "corrente_estator_amp": 28.0,
  "pressao_hidraulica_bar": 160.0,
  "nivel_ruido_db": 53.0
}
```

Respostas comuns: `200` com a predição, `422` quando o corpo não corresponde ao schema ou `503` se o modelo ainda não foi treinado.

O endpoint recebe uma leitura isolada. Para os atributos temporais, usa o valor atual como média móvel e desvio zero. Uma integração real deve manter o histórico de cada célula e calcular as mesmas variáveis temporais do pipeline antes de prever.

### `POST /inspect/weld`

Recebe um formulário `multipart/form-data` com o campo `imagem` (JPG ou PNG). A região selecionada pelo navegador é enviada nos campos opcionais `roi_x`, `roi_y`, `roi_w` e `roi_h`; envie os quatro ou nenhum.

```bash
curl -X POST http://127.0.0.1:8000/inspect/weld \
  -F "imagem=@cordao.jpg" \
  -F "roi_x=120" -F "roi_y=80" -F "roi_w=500" -F "roi_h=180"
```

A resposta inclui `avaliacao`, `motivos`, contagens e `mapa_visual_base64`, uma imagem PNG codificada em Base64. O site já decodifica e mostra essa imagem. A rota retorna `400` para imagem/área inválida e `422` se apenas parte das coordenadas da região for enviada.

### Outras rotas

| Rota | Uso |
|---|---|
| `GET /health` | Confere se a API está ativa e se o arquivo do modelo existe |
| `GET /api/dashboard-data` | Fornece os dados preparados para os gráficos |
| `GET /api/model-report` | Fornece as métricas do último treino |
| `GET /docs` | Interface interativa Swagger |

## Pipeline de dados

O notebook [`notebooks/01_tratamento_dados.ipynb`](notebooks/01_tratamento_dados.ipynb) é a versão explicada e interativa do tratamento. `src/pipeline.py` mantém a mesma lógica para automação da API e do Docker:

1. Calcula a taxa de ausência por célula e liga antes do preenchimento.
2. Substitui leituras fora dos limites por valores ausentes. Os limites estão em `LIMITES` no próprio script.
3. Aplica Z-score dentro de cada liga para identificar extremos relativos ao material.
4. Ordena por célula e tempo e interpola lacunas de até duas amostras consecutivas. Ausências restantes são preenchidas pela mediana da célula e, como reserva, pela mediana geral.
5. Calcula média móvel de seis observações e desvio-padrão de 24 observações para vibração, torque e vazão.
6. Calcula o Índice de Esforço Mecânico: `IEM = torque × vibração / (vazão + 1)`.
7. Cria razões entre sensores e média da liga para normalização demonstrativa.

**Observação sobre as janelas:** o código usa contagem de registros (6 e 24) como aproximação para 30 minutos e duas horas, conforme a atividade. Embora o CSV tenha uma linha a cada cinco minutos, os identificadores de célula se alternam; portanto, o intervalo entre duas observações da mesma célula pode ser maior. Uma versão de produção deve usar janelas temporais baseadas em `timestamp` e confirmar a frequência por equipamento.

## Modelos e resultados

`src/treinar_modelo.py` ordena os dados por tempo, usa os primeiros 70% para treino e os últimos 30% para teste, compara Random Forest e Extra Trees e usa `class_weight="balanced"` para lidar com o desbalanceamento. O critério de seleção é o recall médio das classes de falha 1, 2 e 3. O script imprime as matrizes de confusão e salva o melhor modelo e seu relatório.

Resultado do treino atual:

| Modelo | Recall médio das classes 1–3 |
|---|---:|
| Random Forest (selecionado) | 63,2% |
| Extra Trees | 54,8% |

Recall por classe do Random Forest selecionado:

| Classe | Recall |
|---|---:|
| Normal (0) | 99,0% |
| Desgaste (1) | 71,2% |
| Refrigeração (2) | 70,8% |
| Desalinhamento/trinca (3) | 47,4% |

Matriz de confusão do teste temporal (linhas = classe real; colunas = classe prevista; ordem 0, 1, 2, 3):

| Real / prevista | 0 | 1 | 2 | 3 |
|---|---:|---:|---:|---:|
| 0 | 2.537 | 12 | 12 | 2 |
| 1 | 12 | 94 | 4 | 22 |
| 2 | 30 | 10 | 119 | 9 |
| 3 | 25 | 42 | 5 | 65 |

Assim, **o modelo atual não atinge a meta de 90% de recall para falhas**. As métricas podem mudar se o CSV, as dependências ou o código forem alterados; rode o treino novamente para atualizar o relatório do dashboard.

O script também imprime um indicador chamado OEE estimado, construído apenas a partir das classes previstas. Ele é um proxy didático e **não é o OEE real da fábrica**. O cálculo de OEE requer dados de tempo planejado, paradas, velocidade/desempenho e peças boas e totais.

## Inspeção visual

`src/visao.py` usa OpenCV para suavizar a imagem, aplicar Canny e procurar pequenos contornos aproximadamente circulares. O mapa falso-colorido usa diferenças locais de brilho e textura para destacar regiões de maior contraste. Os limites são parâmetros iniciais definidos em pixels e não foram calibrados com uma base de soldas classificadas.

Uma fotografia RGB não contém medição de temperatura. Portanto:

- o mapa devolvido **não é termografia**;
- “Sem alerta visual pelo filtro” não significa que a solda foi aprovada;
- reflexos, iluminação, ferrugem, ângulo e textura podem alterar o resultado;
- a seleção manual da região ajuda a evitar que o fundo entre na análise;
- qualquer critério de aceitação deve ser validado por inspetor e por imagens rotuladas.

Para regenerar as duas amostras de teste:

```powershell
.\.venv\Scripts\python.exe scripts/gerar_amostras_visao.py
```

## Docker

O Dockerfile instala as dependências, treina o modelo durante a construção da imagem e inicia o FastAPI. Na raiz do projeto:

```bash
docker compose up --build
```

Abra <http://localhost:8501>. A documentação da API fica em <http://localhost:8501/docs>. Para parar os contêineres, use `Ctrl+C` ou execute `docker compose down` em outro terminal.

## Estrutura dos arquivos

```text
.
├── assets/
│   ├── amostras_visao/       # PNGs sintéticos para testar a inspeção
│   └── *.svg                # Capa e ilustrações do site
├── dados_sensores_vulcantech.csv
├── notebooks/
│   └── 01_tratamento_dados.ipynb # Tratamento explicado célula por célula
├── scripts/
│   └── gerar_amostras_visao.py
├── src/
│   ├── api.py               # Rotas FastAPI e páginas do site
│   ├── pipeline.py          # Limpeza e atributos derivados
│   ├── treinar_modelo.py    # Treino, comparação e relatório
│   └── visao.py             # Análise visual experimental
├── web/
│   ├── index.html           # Capa
│   ├── dashboard.html       # Visão geral
│   ├── sensors.html         # Séries temporais
│   ├── inspection.html      # Upload e resultado visual
│   ├── *.js                 # Interação das páginas
│   └── styles.css
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── requirements-notebook.txt # Inclui o kernel Jupyter
```

## Parecer técnico e limitações

- **LGPD:** o CSV fornecido contém dados de processo e identificadores de célula. Caso a implantação associe dados a operadores, turnos individuais ou produtividade pessoal, a empresa deve avaliar finalidade, acesso, retenção e demais obrigações da [Lei nº 13.709/2018](https://www.gov.br/pt-br/lgpd/lei-no-13-709-18-lei-geral-de-protecao-de-dados-lgpd).
- **Cibersegurança OT/IT:** limitar a API à rede autorizada, autenticar clientes, proteger o tráfego, registrar alterações e separar redes corporativas e industriais. Esta demonstração não se conecta a CLP.
- **EU AI Act:** eventual uso ou comercialização na União Europeia exige análise da finalidade, do papel do sistema e da legislação aplicável. Ver [Regulamento (UE) 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj).
- **ESG:** manutenção preventiva pode ajudar a reduzir refugo, retrabalho, matéria-prima e paradas, mas os ganhos devem ser medidos em piloto comparando consumo, sucata e horas de parada.

Antes de qualquer uso operacional, validar os dados, reduzir vazamento de informação temporal no pré-processamento, calibrar a visão computacional com imagens rotuladas e testar o modelo em períodos futuros e condições reais.
