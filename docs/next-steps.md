# Próximas etapas do ChromaPath

Este é o ponto de retomada atualizado em 8 de setembro de 2026.

## Incrementos concluídos

Foi criado um comparador automático para avaliar uma imagem com os dois fluxos:

1. gerar um SVG diretamente com o VTracer;
2. gerar outro SVG com o pipeline completo do ChromaPath;
3. preservar também a etapa preparada, antes da simplificação final das cores;
4. contar caminhos, cores de preenchimento e tamanho dos três arquivos;
5. salvar os resultados lado a lado em `outputs/`;
6. apresentar um relatório curto no terminal.

Essa ferramenta é destinada ao desenvolvimento. O fluxo principal continua
simples, recebendo somente a imagem e produzindo o SVG final.

O comparador também foi executado sobre os quatro casos locais. A linha de base
com caminhos, cores e tamanho foi registrada em `docs/experiments.md`.

A primeira tolerância adaptativa também foi implementada. Ela escolheu Delta E
1 para o cubo, 7 para Perflex e Mickey e 8 para a vaca, produzindo arquivos
idênticos aos quatro resultados anteriormente aprovados.

A primeira limpeza adaptativa de pequenas regiões também foi concluída. Em um
par controlado de mascotes limpo e ruidoso, ambos terminaram com 17 caminhos e
cinco cores. A regra só atua quando encontra um fundo uniforme e evidência
suficiente de resíduos, preservando a versão limpa sem alterações.

A proteção de detalhes separados também ganhou um caso reproduzível. Três
losangos pequenos e alinhados foram mantidos enquanto 14 resíduos aleatórios
foram descartados; os SVGs limpo e ruidoso ficaram idênticos.

Um terceiro caso protege uma única estrela irregular pela relação de forma,
posição e cor com o objeto principal. As versões limpa e ruidosa também ficaram
idênticas byte por byte.

## Próximo incremento

A primeira rodada de geometria foi concluída sem alterar o comportamento do
produto. O [ensaio](geometry.md) tem 24 entradas controladas e seis ajustes.
Comprimento 10 reduz 25,8% dos segmentos no total, mas piora alguns detalhes
locais; união de curvas a 60 cria uma franja adicional e foi rejeitada como
padrão geral. Não implementar uma regra por resolução ou número de cores com
base apenas nesses resultados. Os 37 testes passaram e os 36 SVGs da comparação
anterior ficaram byte a byte iguais. Detalhes em [experimentos](experiments.md).

O diagnóstico da franja subpixel também foi concluído. Nas seis entradas de
`seam`, o raster preparado é idêntico à entrada e o SVG preparado é idêntico
ao final. O coral indevido nasce no tracing e depende da filtragem do backend:
`filter_speckle` 1, 2 e 4 preservam o problema; 0 remove o coral, mas multiplica
caminhos/cores e mantém outros resíduos. Mudar precisão, diferença de camadas
ou hierarquia não resolveu. Normalizar misturas na borda externa também foi
testado e rejeitado por piorar silhuetas e diagonais. Não repetir essas trocas
como se fossem correções ainda não testadas.

**Próximo trabalho exato: investigar a filtragem interna do backend fixado.**

1. Partir de `tools/fringe_experiment.py` e dos relatórios `fringe-final`/`fringe-final8`
   documentados em `docs/experiments.md`. Manter o controle de produção.
2. Obter e inspecionar as fontes correspondentes ao pacote Python 0.6.15 e às
   dependências Rust efetivamente usadas; não usar `master` como equivalente.
3. Localizar por que um limite de fragmentos tão pequeno altera a cobertura de
   uma borda longa. Separar descarte de clusters, atribuição de cores e
   empilhamento dos caminhos. A etapa externa foi localizada, não essa função
   interna; ainda não afirmar qual desses mecanismos é o culpado.
4. Se houver correção pequena viável, testar em isolamento contra a mesma
   baseline. Se depender de mudança significativa do backend, comparar uma
   versão nova em ambiente separado antes de propor migração; não atualizar
   `requirements.txt` automaticamente.
5. Exigir redução da franja sem novos tons/resíduos, sem frestas e sem piorar
   silhueta, pontas ou diagonais. Repetir os 24 casos geométricos, os 43 testes
   e os 36 SVGs anteriores antes de considerar qualquer alteração de produção.

O ensaio padrão foi repetido sem diferenças nos SVGs de controle. A suíte
atual tem **43 testes aprovados** e os 36 SVGs anteriores seguem byte a byte
iguais. O candidato `tools/edge_mixture.py` existe apenas para reprodução da
hipótese rejeitada; não o conectar ao pré-processamento de produção.

Os comprimentos 6–10 ficam para uma rodada posterior com mais curvas pequenas
e casos reais. A referência de cor Delta E 8, quinas 45 e VTracer 0.6.15 continuam
mantidos; investigar VTracer 1.0 separadamente, sem misturar as causas.

## Por que o comparador veio primeiro

O comparador cria uma referência repetível para avaliar mudanças futuras. Com
ele, poderemos melhorar uma imagem e verificar se vaca, Logo Perflex, cubo mágico
e Mickey sofreram regressões, sem depender somente da memória visual.

## Sequência depois do comparador

1. Reunir imagens próprias ou com licença livre para testes públicos.
2. Refinar a tolerância adaptativa de agrupamento das cores.
3. Detectar pequenas regiões e distinguir ruído de detalhes relevantes.
4. Avaliar o VTracer 1.0 em ambiente separado, sem substituir de imediato a
   versão `0.6.15` que já funciona.
5. Melhorar a geometria final: quinas, curvas, número de nós e frestas.
6. Consolidar o projeto Python e disponibilizar o comando `chromapath`.
7. Criar uma interface web simples, inicialmente com o motor Python existente.
8. Publicar a aplicação web e manter a linha de comando como alternativa.

## Direção da versão 1.0

A versão 1.0 será voltada a logos, ícones, mascotes e ilustrações vetorizáveis,
sem a promessa de tratar fotografias perfeitamente. A interface principal será
web, com envio da imagem, comparação visual e download do SVG. Um instalador de
desktop ficará como possibilidade posterior, caso exista necessidade real.

## Decisões mantidas

- O programa não exigirá um número fixo de cores no fluxo principal.
- As escolhas técnicas deverão ser automáticas e baseadas na própria imagem.
- Machine learning só será considerado se as heurísticas tradicionais se
  mostrarem insuficientes.
- Gradientes e efeitos metálicos podem ser simplificados; eles não são a
  prioridade do MVP.
- O VTracer continuará como backend enquanto atender à qualidade necessária.
- Monetização e anúncios só serão avaliados depois de qualidade, experiência de
  uso e público real.
