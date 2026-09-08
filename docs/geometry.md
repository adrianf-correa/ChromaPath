# Ensaio de geometria

Ferramenta de desenvolvimento, isolada do pipeline. Nenhum parâmetro adicional
é solicitado ao usuário comum. Resultados e decisões: [experimentos](experiments.md).

## Reproduzir

Use o ambiente Python do README e Node.js 22 ou mais recente com npm. Instale
o renderizador opcional, cujas dependências estão fixadas no lockfile de `tools/`:

```powershell
npm ci --prefix tools
python -m tools.geometry_experiment --output outputs/geometry/meu-ensaio
```

O destino precisa ser **novo**: a ferramenta recusa sobrescrever outro ensaio.
O programa principal e `python -m unittest discover -s tests -v` continuam
funcionando sem Node ou sharp. Não há dependência nova em `requirements.txt`.
Os testes Python cobrem cálculos e controle; o comando acima é a verificação
integrada que também exercita o renderizador.

Para conferir o efeito da grade de medição com amostragem mais fina:

```powershell
python -m tools.geometry_experiment --output outputs/geometry/conferencia8 --sizes 96 --phases 0 --render-scale 8
```

`--node` permite informar outro executável Node. Se sharp já estiver instalado
em um ambiente de ferramentas separado, `NODE_PATH` pode indicar seus módulos.
Esse foi o ambiente utilizado na sessão de 08/09: Python 3.12.14, Node 24.19.0,
sharp 0.35.4, librsvg 2.62.91 e as dependências Python fixadas no projeto.
O lançador da `.venv` local falhou; foi usado outro Python 3.12 com os pacotes
já instalados nela, sem recriar ou alterar o ambiente do usuário.

## O que é comparado

Quatro cenas originais, definidas em `tools/geometry_fixtures.py`:

- `arcs`: anel, círculos e curva pequena interna;
- `tips`: estrela com quinas côncavas e pontas agudas;
- `diagonals`: duas barras inclinadas;
- `seam`: duas regiões adjacentes separadas por uma curva em S.

Cada cena usa 96, 192 e 384 pixels, com deslocamento de 0 ou 0,5 pixel da
entrada. A posição muda, não a forma ideal. São 24 entradas e seis ajustes:

| Ajuste | Única diferença para produção |
| --- | --- |
| current | Nenhuma; usa a função de produção |
| length6 / length8 / length10 | `length_threshold` 6 / 8 / 10 |
| corner60 | `corner_threshold` 60, em vez de 45 |
| splice60 | `splice_threshold` 60, em vez do padrão 45 |

O pré-processamento é executado uma vez por entrada e compartilhado entre
ajustes. Cores continuam sendo simplificadas pelo código atual. O controle
experimental precisa coincidir exatamente com o SVG da função de produção.
Um teste confirma também que comprimento explícito 4 coincide com o padrão.

O SVG original é renderizado diretamente na resolução de entrada e a 4× para
referência. A saída é renderizada pelo mesmo motor a 4×. A referência não é um
SVG traçado pelo VTracer, nem uma imagem ampliada da entrada.

## Métricas e limites

- **Segmentos:** soma de comandos L e C, incluindo repetições implícitas.
  M, C, L e Z são contabilizados separadamente. Não é contagem exata de nós
  editáveis: os dois controles de uma Bézier e o fechamento não são âncoras
  independentes. O parser aceita apenas o subconjunto emitido pelo backend
  atual e rejeita outros comandos, em vez de produzir um número falso.
- **Área divergente:** quantidade de pixels cuja região de cor difere da
  referência. Dividida pela resolução² para comparar as escalas. A média
  publicada dá o mesmo peso às 24 entradas, não aos pixels de imagens maiores.
- **Borda:** distância euclidiana simétrica entre bordas rasterizadas, com
  média, p95 e máximo, convertida para pixels da entrada. Medimos a silhueta
  e cada cor separadamente. Região ausente é sinalizada; distância indefinida
  é `null`, nunca zero. Isso não é uma distância vetorial contínua exata.
- **Regiões locais:** área divergente e área descoberta nas pontas, círculo
  pequeno, quina e faixa interna da emenda. Evitam esconder perdas pequenas
  sob a área do restante do desenho. Não recortamos bordas para calcular
  distâncias, pois o próprio recorte criaria bordas artificiais.
- **Fresta:** pixels de fundo onde a referência era preenchida, na região
  interna da emenda. Não confundir troca azul/coral com um buraco branco.

A classificação considera misturas de antialias entre pares da paleta
conhecida e escolhe a cor de maior cobertura. Proximidade à cor pura mais
próxima foi rejeitada: inventava regiões coral na transição azul/branco.
Um teste protege esse caso. Esse classificador NÃO foi criado para fotografias,
gradientes, paletas arbitrárias ou para medir fidelidade de cores.

O máximo por cor pode ser alto por causa de uma franja **estreita e comprida**:
significa que essa cor apareceu longe de sua região esperada, não que o objeto
inteiro se deslocou tantos pixels. Por isso é necessário olhar a silhueta,
área, resultados renderizados e métricas locais juntos. Uma grade a 4× pode
perder artefatos menores que 0,25 pixel; a conferência a 8× não elimina todos
os efeitos do renderizador. Os dois usam librsvg, não motores independentes.

## Arquivos produzidos

Cada caso contém `reference.svg`, `reference.png`, `input.png`, `prepared.png`
e os seis SVGs com suas renderizações. `report.json` reúne as métricas completas,
parâmetros, versões, hashes das ferramentas e relatórios do pré-processamento.
`summary.csv` facilita a comparação das principais medidas. Os manifestos de
renderização registram exatamente quais arquivos foram processados.

As saídas ficam ignoradas pelo Git; os geradores e testes são versionados.
As versões das bibliotecas de renderização devem ser comparadas antes de tratar
diferenças mínimas entre máquinas como regressão do ChromaPath.
