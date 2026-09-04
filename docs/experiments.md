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
