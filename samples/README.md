# Imagens de teste

Coloque nesta pasta as imagens usadas durante o desenvolvimento.

Os arquivos adicionados diretamente a `samples/` são ignorados pelo Git para
evitar publicar materiais sem licença de redistribuição.

A subpasta `fixtures/` contém somente imagens originais e redistribuíveis usadas
pelos testes automatizados. O par do robô apresenta o mesmo desenho em uma
versão limpa e outra com ruído controlado. O par `detached-details` acrescenta
três pequenos losangos legítimos separados do objeto principal para confirmar
que eles não sejam confundidos com resíduos. O par `unique-detail` faz o mesmo
com uma única estrela irregular relacionada visualmente ao emblema.

As amostras determinísticas podem ser recriadas executando
`python tools/generate_fixtures.py`.

As novas formas geométricas originais são definidas em
`tools/geometry_fixtures.py`. O [ensaio geométrico](../docs/geometry.md) gera
suas referências SVG e entradas PNG dentro de `outputs/`, sem sobrescrever
os pares acima. São quatro cenas em três resoluções e duas posições na grade.
