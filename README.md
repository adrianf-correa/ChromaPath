# Raster2SVG

Ferramenta experimental de vetorização automática de imagens raster, criada em
Python para estudo de processamento de imagens e geração de SVG.

O escopo atual prioriza logos, mascotes, ícones e ilustrações com formas
vetorizáveis. Fotografias não são um objetivo do MVP.

O projeto utiliza o VTracer como motor de vetorização. O objetivo é desenvolver
um pré-processamento próprio capaz de reduzir ruídos e variações de cor pouco
relevantes sem impor uma quantidade fixa de cores para todas as imagens.

> Status: MVP funcional em desenvolvimento. A conversão automática já inclui
> análise local, pré-processamento e geração do SVG.

## Funcionalidades atuais

- Leitura de imagens PNG, JPG e WEBP.
- Correção da orientação EXIF.
- Preservação de transparência por meio do formato RGBA.
- Vetorização colorida com VTracer.
- Geração automática do arquivo SVG.
- Análise das cores exatas e dominantes da imagem.
- Comparação de proximidade entre cores dominantes.
- Conversão de RGB para CIELAB e cálculo de distância perceptual (Delta E).
- Agrupamento diagnóstico de cores perceptualmente semelhantes.
- Estimativa de ruído local baseada em pixels vizinhos.
- Decisão automática entre preservar uma imagem chapada ou aplicar o filtro
  bilateral adaptativo.
- Identificação do interior de regiões quase pretas com preservação das bordas.
- Análise do canal alfa e remoção conservadora de franjas quase transparentes.
- Detecção de cantos do VTracer ajustada para preservar melhor quinas.
- Simplificação perceptual dos preenchimentos do SVG sem alterar seus caminhos.
- Escolha automática da área mínima de pequenas regiões descartadas pelo
  VTracer.

## Requisitos

- Python 3.12 ou mais recente.
- Dependências registradas em `requirements.txt`.

## Preparação do ambiente

No PowerShell, dentro da pasta do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Quando o ambiente estiver ativo, o terminal exibirá `(.venv)` antes do caminho.

## Vetorizar uma imagem

```powershell
python main.py samples/sua-imagem.png
```

Por padrão, o resultado será criado em `outputs/sua-imagem.svg`.

O fluxo principal analisa primeiro a variação local. Imagens predominantemente
chapadas seguem sem o filtro bilateral; imagens com muita variação recebem uma
passagem do filtro. Em seguida, o VTracer usa o modo `stacked`, precisão de cor
interna 5 e limite de cantos de 45 graus. Por fim, preenchimentos com distância
de até Delta E 8 são agrupados. Essas decisões não precisam ser informadas pelo
usuário e não impõem uma quantidade fixa de cores.

Para escolher outro caminho de saída:

```powershell
python main.py samples/vaca.png --output outputs/outro-nome.svg
```

## Analisar as cores

O analisador é uma ferramenta de desenvolvimento. Ele não altera a imagem nem o
SVG: apenas mostra informações que ajudarão a construir o pré-processamento.

```powershell
python -m src.color_analysis samples/sua-imagem.png --top 20
```

O argumento opcional `--top` define quantas cores dominantes serão mostradas.
Seu valor padrão é 10 e o mínimo aceito é 2.

O relatório apresenta:

- quantidade de pixels visíveis;
- quantidade de cores RGB exatas;
- cores mais frequentes e suas porcentagens;
- pares de cores dominantes com menor distância perceptual;
- comparação entre distância RGB e Delta E;
- famílias provisórias de cores próximas;
- estatísticas de Delta E entre pixels vizinhos horizontais e verticais.
- quantidade de tons quase pretos no interior e nas bordas das formas.
- distribuição de pixels transparentes, semitransparentes e opacos.

Os pares e as famílias são calculados no espaço CIELAB, que aproxima melhor a
percepção humana de cor. A tolerância usada nas famílias ainda é fixa e serve
somente para diagnóstico. Nenhuma dessas análises altera a imagem.

## Inspecionar o pré-processamento

```powershell
python -m src.preprocess samples/sua-imagem.png
```

Esse comando de desenvolvimento executa o mesmo pré-processamento usado pelo
fluxo principal, mas preserva o PNG intermediário. Ele analisa a variação local,
estima uma tolerância Delta E e aplica uma passagem do filtro bilateral em
CIELAB.

São gerados dois arquivos para comparação:

- `outputs/sua-imagem-preprocessed.png`;
- `outputs/sua-imagem-preprocessed.svg`.

No caso de teste atual, o SVG passou de 109 para 46 caminhos e de 100 para 42
cores de preenchimento. O tamanho caiu de 137.364 para aproximadamente 109.675
bytes.

## Executar os testes

O projeto usa inicialmente o `unittest`, incluído no próprio Python. Para
executar todos os testes dentro da pasta `tests`:

```powershell
python -m unittest discover -s tests -v
```

Os testes verificam os dois ramos da decisão automática do filtro: uma imagem
chapada deve preservar os pixels, enquanto uma imagem com variação local deve
receber o filtro bilateral. Uma imagem sintética pequena também confirma que a
normalização corrige variações quase pretas no interior sem alterar sua borda.
Outro teste garante que o limite da franja remove alfa 31, mas preserva alfa 32.
Os testes do pós-processamento verificam que cores próximas são unificadas,
cores distantes continuam separadas e a quantidade de caminhos não muda.
Também é testada a escolha entre a limpeza padrão de 4 pixels e a limpeza mais
forte de 16 pixels para franjas opacas grandes e fragmentadas.

## Casos de teste

Os exemplos possuem problemas diferentes e ajudam a evitar que o algoritmo seja
ajustado para funcionar em apenas uma imagem. Essas imagens são usadas
localmente e não são distribuídas no repositório:

- `vaca.png`: possui muitas variações pequenas de cor. É usada para avaliar a
  redução de ruído sem destruir contornos importantes;
- `Logo Perflex.png`: possui poucas cores, mas o desenho útil tem poucos pixels
  de altura. É usada para avaliar curvas, diagonais, pontas e traços finos em
  imagens de baixa resolução.

No segundo caso, o filtro de cores não aumentou nem reduziu a quantidade de
caminhos: tanto a versão direta quanto a pré-processada produziram 11 caminhos.
Mesmo assim, as duas perderam qualidade geométrica. Isso mostra que reduzir
cores e reconstruir formas são problemas relacionados, mas diferentes.

Uma ampliação experimental com interpolação Lanczos foi rejeitada porque criou
208 caminhos e 158 cores de preenchimento. Em seguida, foi testado apenas o
limite de detecção de cantos do VTracer, reduzido de 60 para 45 graus. Essa
variante preservou os 11 caminhos e as 10 cores da versão direta, melhorou
visualmente as quinas e reduziu o SVG de 9.703 para 7.756 bytes.

Na vaca, a normalização protegida das regiões quase pretas reduziu 636 cores
interiores para uma cor predominante, sem alterar o Logo Perflex, cujo interior
preto já era uniforme. O SVG da vaca passou de 46 para 43 caminhos e de 42 para
39 cores. A inspeção visual também mostrou um contorno mais redondo nos olhos.
Uma pequena fresta rosa que aparecia junto a uma região preta deixou de surgir
após a normalização, sem necessidade de pós-processar as camadas do SVG.
Com a simplificação final dos preenchimentos, a vaca ficou com 43 caminhos e 9
cores.

O `Cubo mágico.png` testa gradientes reais e transparência. O filtro bilateral
foi corretamente dispensado nesse caso para não simplificar os gradientes. A
remoção de 6.867 pixels com alfa entre 1 e 31 limpou a franja externa: o SVG
passou de 397 para 29 caminhos, de 168 para 12 cores e de 298.725 para 141.429
bytes, com melhora visual aprovada. O pós-processamento reduziu a paleta final
para 5 cores, preservando um segundo azul suficientemente diferente.

No Logo Perflex, a configuração de cantos e a simplificação final produziram 11
caminhos e 4 cores.

O `Mickey_Mouse.webp` testa uma ilustração com várias cores, detalhes finos e
uma franja externa gravada como pixels totalmente opacos. A escolha automática
de uma limpeza mínima de 16 pixels reduziu o SVG de 135 para 31 caminhos. A
normalização dos preenchimentos muito escuros removeu tons marrons dos
contornos, deixando o resultado final com 7 cores.

## Pipeline atual

```text
Imagem raster
    ↓
Leitura e normalização com Pillow
    ↓
Conversão para pixels RGBA
    ↓
Análise e limpeza adaptativa da transparência
    ↓
Análise local em CIELAB
    ↓
Filtro bilateral adaptativo
    ou preservação dos pixels originais
    ↓
Normalização experimental do interior quase preto
    ↓
VTracer
    ↓
Agrupamento perceptual dos preenchimentos do SVG
    ↓
SVG
```

## Estrutura do projeto

```text
raster2svg/
├── main.py                 # Entrada principal da aplicação
├── requirements.txt        # Dependências Python
├── samples/                # Imagens usadas durante o desenvolvimento
├── outputs/                # SVGs gerados localmente
├── tests/                  # Testes automatizados
└── src/
    ├── vectorize.py        # Backend de geração SVG com VTracer
    ├── color_analysis.py   # Diagnóstico e comparação de cores
    ├── preprocess.py       # Pré-processamento adaptativo
    └── svg_postprocess.py  # Simplificação das cores do SVG
```

## Limitações atuais

- O agrupamento diagnóstico considera apenas as cores dominantes solicitadas.
- A tolerância perceptual das famílias ainda é fixa e não adaptativa.
- A estimativa adaptativa usa uma heurística que precisa de mais casos de teste.
- A decisão de pular o filtro usa provisoriamente 85% de vizinhos idênticos como
  indicação de uma imagem chapada e 97% de vizinhos próximos para distinguir
  ruído de transições relevantes.
- A franja alfa só é removida quando pelo menos 95% dos pixels visíveis são
  quase opacos; o limite descartado ainda é fixo em alfa 31.
- A simplificação dos preenchimentos usa provisoriamente um limite fixo de
  Delta E 8.
- A limpeza de 16 pixels é escolhida provisoriamente para imagens transparentes
  com pelo menos 100.000 pixels visíveis, nenhuma semitransparência e ao menos
  1.000 cores exatas.
- Imagens em que o desenho ocupa poucos pixels de altura ainda produzem curvas
  e pontas grosseiras.
- Gradientes, brilhos e efeitos metálicos podem ser simplificados em faixas ou
  cores mais chapadas. Esse comportamento é aceito no escopo atual do MVP.
- Ruído, regiões pequenas e detalhes relevantes ainda não são classificados.
- O projeto ainda não possui interface gráfica.

## Próximas etapas

1. Validar o pipeline com mais tipos de imagem.
2. Tornar adaptativo o limite de simplificação dos preenchimentos.
3. Detectar e tratar regiões pequenas indesejadas.
4. Adicionar comparações automatizadas dos SVGs de referência.
5. Avaliar outros backends caso o VTracer limite a qualidade desejada.

## Objetivo de aprendizado

Além de produzir uma ferramenta utilizável, este projeto serve para praticar
Python, processamento de imagens, organização de código, testes e documentação
de um projeto público.
