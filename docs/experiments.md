# Registro de experimentos

Este documento reúne observações feitas durante o desenvolvimento do ChromaPath.
Ele não descreve garantias do programa: os números representam checkpoints do
MVP e podem mudar conforme o pipeline evolui.

As imagens citadas são mantidas apenas no ambiente local porque nem todas
possuem licença de redistribuição.

## Objetivo dos casos de teste

Cada imagem foi escolhida para revelar um tipo diferente de problema:

| Caso | Problema observado | O que avaliamos |
| --- | --- | --- |
| Vaca | Muitos tons quase iguais e regiões quase pretas | Redução de ruído, cores e artefatos sem destruir contornos |
| Logo Perflex | Logotipo com poucos pixels de altura | Quinas, curvas, diagonais, pontas e traços finos |
| Cubo mágico | Transparência, bordas externas e gradientes | Limpeza de franjas sem simplificar excessivamente as faces |
| Mickey | Muitas cores e uma franja externa totalmente opaca | Remoção adaptativa de fragmentos e preservação dos contornos |
| Robô limpo/ruidoso | Mesmo desenho com resíduos controlados | Remoção de pequenas regiões sem apagar detalhes legítimos |
| Detalhes separados | Três símbolos legítimos e ruído aleatório | Proteção de padrões pequenos afastados do objeto principal |
| Detalhe único | Uma estrela irregular e ruído aleatório | Proteção contextual sem depender de repetição |

## Linha de base do comparador

Em 4 de setembro de 2026, os quatro casos foram processados pelo comparador. A
baseline utiliza a imagem original diretamente na integração com o VTracer, sem
o pré-processamento e a simplificação final de cores do ChromaPath.

| Caso | Baseline: caminhos / cores / tamanho | ChromaPath: caminhos / cores / tamanho | Redução de caminhos | Redução de cores |
| --- | --- | --- | ---: | ---: |
| Vaca | 55 / 47 / 104,1 KB | 43 / 8 / 101,9 KB | 21,8% | 83,0% |
| Logo Perflex | 11 / 10 / 7,6 KB | 11 / 4 / 7,6 KB | 0% | 60,0% |
| Cubo mágico | 424 / 173 / 786,1 KB | 29 / 5 / 138,1 KB | 93,2% | 97,1% |
| Mickey | 131 / 126 / 145,3 KB | 31 / 7 / 84,2 KB | 76,3% | 94,4% |

Menos caminhos e cores normalmente tornam o SVG mais compacto e editável, mas
esses números não comprovam sozinhos uma melhora visual. Toda alteração do
pipeline deve combinar as métricas com a inspeção dos contornos e detalhes.

## Primeira tolerância adaptativa

O limite único de Delta E 8 foi substituído por uma escolha conservadora. O
algoritmo simula tolerâncias de 1 a 12 e procura o início do patamar de cores que
contém a referência já validada. As escolhas foram:

| Caso | Delta E escolhido |
| --- | ---: |
| Cubo mágico | 1 |
| Logo Perflex | 7 |
| Mickey | 7 |
| Vaca | 8 |

Os quatro SVGs adaptativos ficaram idênticos byte por byte aos resultados
anteriormente aprovados com Delta E 8. Isso confirma a ausência de regressão
neste conjunto e permite usar a menor tolerância que preserva a paleta validada.
A referência 8 ainda funciona como uma proteção interna; novos casos serão
necessários para tornar a decisão progressivamente menos dependente dela.

## Vaca

A primeira passagem de pré-processamento reduziu o SVG de 109 para 46 caminhos
e de 100 para 42 cores de preenchimento. O tamanho passou de 137.364 para cerca
de 109.675 bytes.

A normalização protegida das regiões quase pretas reduziu 636 cores interiores
para uma representante predominante. Depois dessa etapa, o SVG ficou com 43
caminhos e 39 cores antes da simplificação final dos preenchimentos. A inspeção
visual também mostrou contornos mais regulares nos olhos e removeu uma pequena
fresta rosa próxima de uma região preta.

Esse caso mostrou que a limpeza de cores deve distinguir interior e borda. Uma
substituição global dos tons escuros corrigiria o preto, mas poderia deformar os
limites das formas.

## Logo Perflex

O pré-processamento de cores não mudou a quantidade de caminhos: tanto a versão
direta quanto a pré-processada produziram 11. Mesmo assim, ambas perderam
qualidade geométrica por causa da baixa resolução da imagem.

Uma ampliação com interpolação Lanczos foi testada e rejeitada. Ela criou 208
caminhos e 158 cores, realçando o antialiasing em vez de reconstruir as formas.

Em seguida, somente o limite de detecção de cantos do VTracer foi alterado de 60
para 45 graus. Essa variação preservou os 11 caminhos, melhorou visualmente as
quinas e reduziu o arquivo de 9.703 para 7.756 bytes. O experimento ajudou a
separar dois problemas diferentes: simplificação de cores e reconstrução de
geometria.

## Cubo mágico

O filtro bilateral foi dispensado automaticamente para preservar os gradientes.
A remoção de 6.867 pixels com alfa entre 1 e 31 limpou a franja externa. Nesse
checkpoint, o SVG passou de 397 para 29 caminhos, de 168 para 12 cores e de
298.725 para 141.429 bytes. O pós-processamento reduziu a paleta final para cinco
cores e preservou um segundo azul perceptualmente diferente.

O caso mostrou que pequenas variações em um gradiente não devem gerar dezenas
de cores, mas diferenças amplas ainda podem representar tons relevantes.

## Mickey

Essa imagem possui várias cores, detalhes finos e uma franja externa formada por
pixels totalmente opacos. Como não havia semitransparência para orientar a
limpeza, o pipeline escolheu uma remoção mínima de regiões mais forte. O SVG foi
reduzido de 135 para 31 caminhos.

A normalização dos preenchimentos muito escuros também removeu tons marrons que
apareciam nos contornos. Esse resultado motivou uma regra distinta para imagens
transparentes grandes, com muitas cores exatas e bordas opacas fragmentadas.

## Robô limpo e ruidoso

Um mascote original foi gerado em duas versões: uma limpa e outra com pequenos
fragmentos isolados e saliências encostadas à silhueta. A baseline da versão
ruidosa produziu 56 caminhos e 54 cores, contra 19 caminhos e 19 cores na
versão limpa.

Quando as bordas comprovam a existência de um fundo opaco uniforme, o pipeline
agora localiza componentes minúsculos afastados do objeto principal. Se pelo
menos oito deles forem removidos, a limpeza mínima do VTracer passa de 4 para
32 pixels e uma abertura morfológica limitada atua somente na silhueta externa.

No caso ruidoso, foram removidos 23 fragmentos isolados, com 3.301 pixels, e
seis saliências do contorno, com 226 pixels. As duas versões terminaram com 17
caminhos, cinco cores e Delta E adaptativo 4. A versão limpa não teve nenhum
pixel removido pela nova regra. A inspeção visual ainda encontrou dois pequenos
degraus na parte superior; eles foram aceitos como limitação conhecida, pois
aumentar a agressividade colocaria curvas legítimas em risco.

## Detalhes legítimos separados

Uma segunda amostra determinística adicionou três losangos amarelos pequenos,
alinhados e separados do objeto principal. A primeira execução removeu os três
como se fossem ruído, mostrando que proximidade com o objeto não basta para
reconhecer detalhes relevantes.

A proteção passou a considerar repetição de cor e tamanho, proximidade entre os
componentes, alinhamento e regularidade do espaçamento. Na versão ruidosa, 14
fragmentos aleatórios e 222 pixels foram removidos, enquanto os três losangos
foram preservados. O limite do VTracer permaneceu em 4 pixels para não apagar os
detalhes protegidos. As versões limpa e ruidosa terminaram com 11 caminhos,
cinco cores e arquivos SVG idênticos byte por byte.

## Detalhe único e irregular

Uma terceira amostra determinística substituiu o padrão repetido por uma única
estrela coral separada do emblema. Na primeira execução, a estrela sobreviveu à
limpeza raster, mas foi apagada quando a detecção de ruído elevou a limpeza do
VTracer para 32 pixels.

O pipeline passou a proteger componentes de tamanho limitado que tenham forma
irregular, estejam dentro da zona visual expandida do objeto principal e
reutilizem uma de suas cores dominantes. A presença dessa evidência mantém a
limpeza do VTracer em quatro pixels. Com a regra, a versão ruidosa removeu 14
fragmentos e 222 pixels, preservou a estrela e produziu um SVG idêntico byte por
byte ao da versão limpa: nove caminhos, quatro cores e Delta E 1.

## Heurísticas atuais

Os valores abaixo são provisórios e existem para que possamos testar hipóteses:

- uma imagem é considerada predominantemente chapada quando pelo menos 85% dos
  pares de pixels vizinhos são idênticos;
- 97% de vizinhos perceptualmente próximos ajudam a distinguir ruído local de
  transições relevantes;
- a franja de transparência só é removida quando pelo menos 95% dos pixels
  visíveis são quase opacos;
- resíduos com alfa de 1 a 31 podem ser descartados quando o perfil de
  transparência permite;
- a simplificação dos preenchimentos do SVG utiliza provisoriamente Delta E 8;
- a limpeza mínima padrão do VTracer é de 4 pixels e pode passar para 16 em
  imagens grandes com uma franja opaca muito fragmentada ou para 32 quando a
  análise de fundo uniforme comprova a presença de vários resíduos isolados;
- a limpeza de saliências externas só é ativada após essa comprovação de ruído,
  com escala proporcional à resolução e limite máximo de 21 pixels.
- três ou mais regiões pequenas, próximas, alinhadas e semelhantes em cor,
  tamanho e espaçamento são protegidas como um padrão intencional; quando essa
  proteção é usada, a limpeza mínima do VTracer permanece em 4 pixels.
- um detalhe pequeno único também pode ser protegido quando sua forma é
  irregular, sua posição pertence à zona visual do objeto e sua cor aparece
  entre as cores dominantes da composição.

Esses números não são configurações solicitadas ao usuário. Eles são decisões
internas que deverão se tornar mais adaptativas conforme novos casos forem
avaliados.

## Aprendizados até aqui

- Reduzir cores e melhorar caminhos são problemas relacionados, mas diferentes.
- Aumentar a resolução não recupera automaticamente a geometria original.
- Transparência baixa e franjas totalmente opacas exigem estratégias distintas.
- Uma mesma regra não deve ser calibrada para funcionar em apenas uma imagem.
- Métricas ajudam a comparar resultados, mas a inspeção visual continua
  necessária durante esta fase do projeto.

## 08/09/2026 — geometria: complexidade não basta

### Hipótese e controle

Aumentar o comprimento dos segmentos ou o ângulo de união das curvas poderia
reduzir complexidade sem prejudicar o desenho. Um ensaio anterior já sugeria
redução de bytes, mas não tinha referência geométrica suficiente para decisão.

Antes de qualquer alteração, o Git estava limpo em `5d57204`; os 25 testes
passaram. O comparador existente rodou sobre os seis arquivos locais e os seis
arquivos públicos, salvando 36 SVGs e seus hashes em
`outputs/geometry-baseline-20260908/`. Nenhum arquivo aprovado foi sobrescrito.

Foi criado um [ensaio reproduzível](geometry.md) com quatro cenas originais,
três resoluções e duas fases subpixel: 24 entradas, seis ajustes, 144 saídas.
Cada alternativa modifica somente um parâmetro. A referência é o desenho SVG
original renderizado, não a saída de outro vetorizador. Foram mantidos backend
0.6.15, modo spline/stacked, precisão de cor 5 e o processamento adaptativo atual.

Parâmetros da versão instalada foram conferidos no stub do pacote e na
[documentação da versão Python 0.6.15](https://pypi.org/project/vtracer/0.6.15/):

| Parâmetro | Referência do ensaio | Avaliação nesta sessão |
| --- | --- | --- |
| `corner_threshold` | 45 (decisão anterior do projeto) | Alternativa 60 |
| `length_threshold` | 4, padrão do backend | Alternativas 6, 8, 10 |
| `splice_threshold` | 45, padrão do backend | Alternativa 60 |
| `max_iterations` | Padrão 10 | Mantido; sem evidência para mudar |
| `path_precision` | Padrão 8 | Mantido; reduzir casas não resolve forma |
| `mode` / `hierarchical` | spline / stacked | Mantidos para isolar o experimento |

Não foram utilizados parâmetros da API nova nem feita migração para VTracer 1.0.

### Medição e resultado

Relatório válido: `outputs/geometry/20260908-final/report.json` (renderização
a 4×). A rodada inicial `20260908-length-sweep` foi descartada porque um
classificador por cor pura confundia antialias azul/branco com coral. Esse
defeito da ferramenta foi corrigido e ganhou teste; não houve alteração no
quantizador de produção. A rodada `20260908-coverage-sweep` antecedeu a adição
da métrica separada de silhueta; use `20260908-final` como referência completa.

| Ajuste | Segmentos totais | Área divergente média (% da imagem) |
| --- | ---: | ---: |
| Atual | 1186 | 0,9865 |
| Comprimento 6 | 1038 | 0,9452 |
| Comprimento 8 | 932 | 0,9134 |
| Comprimento 10 | 880 | 0,8942 |
| Quina 60 | 1229 | 0,9972 |
| União 60 | 1127 | 0,9788 |

Comprimento 10 reduziu segmentos em **25,8%**, com melhora média de área.
Isso não constitui uma melhora universal:

- `arcs-192-phase0`: área divergente caiu de 328,94 para 161,31 px², com
  39 → 31 segmentos e máximo de borda mantido em 1 pixel.
- `arcs-96-phase0`: o desenho inteiro melhorou, mas a área perdida no círculo
  pequeno subiu de 6,31 para 10,31 px². Seu tamanho não deve ser sacrificado
  apenas porque a média do anel maior ficou melhor.
- `seam-384-phase0`: área divergente subiu de 256,94 para 285,06 px²; na
  faixa interna da emenda, 143,88 → 171,06 px². Segmentos: 28 → 27.
- `tips-96-phase0`: o máximo de erro de borda continuou em 2,85 pixels; reduzir
  segmentos de 54 para 36 não corrigiu a imprecisão das pontas rasterizadas.

União 60 é um contraexemplo mais claro à redução indiscriminada de complexidade:
em `seam-96-phase0`, 20 → 19 segmentos, mas área divergente 52,69 → 65,56 px².
A franja coral se estende pelo topo da região azul. A distância máxima por cor
passou de 1,25 para 15,50 pixels, enquanto a silhueta permaneceu exata. Isso
mede extensão de cor indevida, **não** um deslocamento global de 15 pixels.
Essa mudança foi rejeitada como padrão geral. Quina 60 também não demonstrou
vantagem agregada; a decisão anterior de 45 foi preservada.

A conferência `20260908-scale8` repetiu as quatro cenas de 96 pixels/fase zero
com medição a 8× (24 saídas). Confirmou as direções dos problemas locais:
perda do círculo 6,22 → 9,95 px² com comprimento 10; área divergente da emenda
52,75 → 66,00 px² com união 60. O máximo por cor desta última foi 19,38 pixels,
mostrando a sensibilidade de franjas muito finas à grade de medição.

Não houve fresta branca detectada na região interna da emenda em nenhuma das
144 saídas da rodada principal. Isso vale para esta fixture stacked, não é
prova de ausência de frestas em qualquer imagem ou renderizador.

### Instabilidade já existente e próximo alvo

Deslocar a cena `seam` apenas meio pixel já produz uma franja coral nas bordas
externas azuis com os ajustes **atuais**. Em 192 pixels, a área divergente é
137,13 px² na fase zero e 517,81 px² na fase 0,5. A inspeção das renderizações
confirmou a franja. Sua origem ainda não foi isolada entre pré-processamento,
tracing e simplificação de cor. Não atribuir causalidade a uma etapa sem teste.

Os círculos também mudam de complexidade com a fase (39 → 51 segmentos em
192 pixels), mesmo sem mudança da forma ideal. Portanto, resolução ou contagem
de cores sozinhas não justificam uma regra adaptativa de geometria.

### Decisão e regressões

Manter TODOS os parâmetros de produção e o backend. Comprimentos 6–10 continuam
como candidatos de pesquisa, não como regra pronta nem abordagem inteiramente
descartada. Rejeitar união 60 como padrão geral. A entrega desta etapa é a
avaliação controlada com um contraexemplo reproduzível, não uma promessa de
melhoria visual aplicada a todas as imagens.

Após o trabalho, o comparador foi repetido em
`outputs/geometry-regression-20260908/`: **36/36 SVGs idênticos byte por byte**
à baseline, abrangendo Perflex, cubo, Mickey, vaca, robô e detalhes únicos e
repetidos. A suíte passou de 25 para **37 testes**, todos aprovados, incluindo
calibração de distância, lacunas, detalhe ausente, antialias e equivalência do
controle. Não foram alterados `src/`, `main.py`, dependências Python nem as
fixtures antigas. Não houve commit automático, push ou exclusão de arquivos.

## 08/09/2026 — origem da franja subpixel e correções rejeitadas

Retomada a partir do commit limpo `d43d9d0`, com os 37 testes aprovados.
Objetivo: localizar a primeira etapa que introduz coral na borda azul da
fixture `seam`, antes de corrigir cores ou geometria indiscriminadamente.

### Causa localizada por etapas

Foi criado `tools/fringe_experiment.py`: três resoluções, fases 0/0,5 e
faixas externas longe da emenda. Resultado nas seis entradas:

- raster preparado idêntico à entrada;
- traçado direto idêntico ao traçado da imagem preparada;
- SVG preparado idêntico ao SVG final;
- coral externo ausente nos rasters e presente já no traçado, na fase 0,5.

Logo, neste caso, nem o pré-processamento nem a simplificação de cores causam
a franja. Ela nasce no backend. O SVG empilha coral no fundo, branco com um
recorte e a região azul por cima. Na fase 0,5, o azul começa mais para dentro
do que a abertura branca, expondo coral numa borda que era azul/branco.

Área de coral indevido nas três faixas externas, em pixels² da entrada:

| Resolução / fase | Entrada | Preparada | Traçado | Final |
| --- | ---: | ---: | ---: | ---: |
| 96 / 0 | 0 | 0 | 0 | 0 |
| 96 / 0,5 | 0 | 0 | 96,00 | 96,00 |
| 192 / 0 | 0 | 0 | 0 | 0 |
| 192 / 0,5 | 0 | 0 | 183,25 | 183,25 |
| 384 / 0 | 0 | 0 | 0 | 0 |
| 384 / 0,5 | 0 | 0 | 363,38 | 363,38 |

O experimento associa o defeito à filtragem do backend: `filter_speckle` 1,
2 e 4 mantêm a franja, enquanto 0 remove o coral indevido. Isso ainda não
identifica a função interna de Rust responsável, nem prova que a filtragem
explique todos os defeitos geométricos do projeto.

### Alternativas controladas

1. **`layer_difference` 0/4/8:** não removeu a franja.
2. **Precisão de cor 8:** não removeu a franja.
3. **Hierarquia cutout:** não resolveu e introduziu outros desvios; rejeitada
   como troca geral nesta versão.
4. **`filter_speckle=0`:** removeu coral indevido, mas preservou franjas de
   tons intermediários e resíduos. Em 192/fase 0,5, o resultado final passou
   de 3 caminhos/3 cores/1.837 bytes para 154 caminhos/13 cores/11.725 bytes.
   A inspeção mostrou faixa cinza e pequenas manchas na emenda. Não adotar.
5. **Normalização localizada de misturas externas:** troca pixels opacos
   matematicamente intermediários por fundo/cor vizinha de maior cobertura.
   Restrita a fundo exatamente uniforme e cores chapadas próximas; não usa
   cores específicas da fixture. Removeu o coral, mas deformou o contorno.

O quinto candidato foi aplicado às 24 entradas do ensaio, mantendo o mesmo
tracing e comparando sempre com o controle de produção:

| Caso | Área divergente atual → candidato (px²) | Máximo da silhueta atual → candidato (px) |
| --- | ---: | ---: |
| seam 96 / 0,5 | 259,25 → 204,94 | 0,71 → 1,25 |
| seam 192 / 0,5 | 517,81 → 429,69 | 0,71 → 1,25 |
| seam 384 / 0,5 | 1.073,56 → 935,38 | 0,71 → 1,50 |
| diagonals 96 / 0 | 131,44 → 149,75 | 0,75 → 1,25 |
| arcs 192 / 0,5 | 267,19 → 305,19 | 0,90 → 0,90 |

A média de área divergente melhorou de 0,9865% para 0,9393%, mas os segmentos
subiram de 1.186 para 1.287 e houve regressões locais. **Rejeitado como regra
de produção.** O código fica isolado em ferramentas para reprodução da hipótese,
não conectado ao motor. Não reduzir a exigência de contorno para aprová-lo.

Não houve fresta branca na faixa interna da emenda com esse candidato. Medir
apenas coral indevido ou apenas frestas teria aprovado uma solução que deforma
a silhueta; os critérios separados cumpriram seu propósito.

### Reprodutibilidade e proteção

- `outputs/geometry/fringe-final/report.json`: diagnóstico final a 4×.
- `outputs/geometry/fringe-final8/report.json`: conferência a 8×. Nela, a franja
  atual nas fases 0,5 foi 96,00 / 183,66 / 364,55 px²; as conclusões se mantêm.
- `outputs/geometry/exterior-snap-sweep/report.json`: candidato nas 24 entradas.
- `outputs/geometry/fringe-regression-sweep/`: ensaio original repetido; mesmos
  resultados das seis configurações, sem alteração dos SVGs de controle.
- `outputs/geometry-fringe-regression/`: os 36 SVGs antigos permaneceram
  idênticos byte por byte. `src/`, `main.py` e dependências não foram alterados.

Foram acrescentados testes da medição de área/extensão da franja, invariância
de escala, separação de cor legítima/fresta e limites do candidato: **43 testes
aprovados** na suíte completa. A hipótese
de borda não foi promovida a correção: a causa foi localizada e as alternativas
simples foram descartadas com evidência. O próximo passo deve investigar a
filtragem interna do backend fixado, não retunar cores ou aumentar suavização.
