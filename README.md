# VulcanTech Smart Metals

Projeto didático de manutenção preditiva com os sensores fornecidos no CSV. O código foi mantido em scripts pequenos para facilitar a leitura e a apresentação.

## O que foi feito

1. `src/pipeline.py` mede os valores ausentes por célula e liga, substitui valores fora dos limites operacionais e outliers por liga, interpola lacunas curtas por célula, cria médias móveis e calcula o Índice de Esforço Mecânico (IEM).
2. `src/treinar_modelo.py` separa os registros em ordem temporal (70%/30%), compara Random Forest e Extra Trees com pesos de classe, mostra matriz de confusão, recall por classe e importância dos atributos. O modelo com melhor recall médio das falhas é salvo com `joblib`.
3. `src/visao.py` aplica Canny, contornos e uma máscara HSV para destacar regiões quentes. `src/api.py` expõe as rotas `/predict`, `/inspect/weld` e `/health`.
4. `Dockerfile` e `docker-compose.yml` preparam uma API local demonstrativa.

## Executar localmente

Use Python 3.10 ou superior. No terminal, na pasta do projeto:

```bash
python -m pip install -r requirements.txt
python src/pipeline.py
python src/treinar_modelo.py
uvicorn api:app --app-dir src --reload
```

Abra `http://127.0.0.1:8000/docs` para enviar uma leitura para `/predict` ou uma imagem PNG/JPEG para `/inspect/weld`. A primeira execução cria `dados_processados/` e `modelos/`.

Para executar em contêiner:

```bash
docker compose up --build
```

## Como interpretar

`tipo_falha`: 0 normal, 1 desgaste de ferramenta, 2 falha de refrigeração, 3 desalinhamento ou trinca. O relatório de classificação evidencia se o recall solicitado foi atingido; não se deve afirmar recall de 90% sem verificar o resultado do teste temporal. Os pesos de classe são uma alternativa simples ao SMOTE.

O OEE impresso é apenas uma estimativa didática calculada com as classes previstas: classes 1 e 3 penalizam disponibilidade e classe 2 penaliza qualidade. O CSV não contém tempo planejado, tempo de parada, peças boas ou peças totais, então não permite calcular o OEE industrial real.

O arquivo não contém fotografias de solda nem imagens térmicas. A API aceita imagens enviadas pelo usuário; os limiares HSV e Canny usados são iniciais e precisam ser calibrados e avaliados com imagens rotuladas antes de qualquer uso operacional. A predição não comanda um CLP: a malha fechada é simulada por uma resposta de API.

## Parecer técnico resumido

- **LGPD:** o CSV fornecido contém medições de processo e identificadores de células, sem nomes de operadores. Se a implantação coletar dados ligados a pessoas (por exemplo, usuário, turno ou produtividade individual), a empresa deve definir finalidade, acesso e retenção e avaliar as obrigações da LGPD. A lei protege dados pessoais de pessoas naturais; dados puramente operacionais não são automaticamente dados pessoais. [Lei nº 13.709/2018](https://www.gov.br/pt-br/lgpd/lei-no-13-709-18-lei-geral-de-protecao-de-dados-lgpd).
- **Cibersegurança OT/IT:** restringir a API à rede industrial autorizada, autenticar clientes, criptografar tráfego, registrar alterações e separar a rede de produção da rede corporativa. Manter um modo seguro de operação manual e não enviar comandos diretamente ao CLP nesta demonstração.
- **EU AI Act:** antes de comercializar ou usar na União Europeia, classificar o sistema conforme sua finalidade e o papel que desempenha. O uso de IA como componente de segurança de produtos regulados pode ter requisitos de alto risco; a classificação depende do caso concreto e não é determinada apenas pelo uso de machine learning. [Regulamento (UE) 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj).
- **ESG:** manutenção planejada e inspeção antecipada podem reduzir refugo, retrabalho, consumo de matéria-prima e paradas. Esses ganhos precisam ser medidos comparando energia, sucata e horas de parada antes e depois de um piloto.

## Limitações

O conjunto é sintético/didático e o modelo pode aprender padrões do gerador dos dados, não da fábrica real. O resultado depende da divisão temporal e da distribuição de cada classe. Validar com dados futuros e revisão de um especialista antes de qualquer decisão de manutenção ou qualidade.
