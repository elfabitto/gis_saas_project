# Guia do Usuário - GIS SaaS

## Bem-vindo ao GIS SaaS! 🗺️

O **GIS SaaS** é uma plataforma online que permite gerar mapas profissionais de forma rápida e automática. Com apenas alguns cliques, você pode transformar seus arquivos GIS em mapas de alta qualidade para apresentações, relatórios e documentos.

## O que você pode fazer

✅ **Upload de Arquivos GIS**: Envie arquivos Shapefile, KML, KMZ, GeoJSON ou GPX  
✅ **Geração Automática**: Crie mapas de localização automaticamente  
✅ **Múltiplos Formatos**: Exporte em HTML interativo, PNG ou PDF  
✅ **Personalização**: Customize cores, títulos e elementos visuais  
✅ **Qualidade Profissional**: Mapas prontos para apresentações e relatórios  

## Primeiros Passos

### 1. Acessando a Plataforma

Abra seu navegador e acesse a plataforma GIS SaaS. Você verá a página inicial com uma apresentação das funcionalidades.

### 2. Criando seu Primeiro Projeto

1. Clique no botão **"Novo Projeto"** na página inicial
2. Preencha as informações básicas:
   - **Nome do Projeto**: Dê um nome descritivo (ex: "Mapa da Fazenda São João")
   - **Descrição**: Adicione detalhes sobre o projeto (opcional)
3. Clique em **"Próximo"** para continuar

### 3. Enviando Arquivos GIS

Na segunda etapa, você pode enviar seus arquivos GIS:

#### Formatos Suportados
- **Shapefile (.shp)**: Formato mais comum em GIS
- **KML (.kml)**: Formato do Google Earth
- **KMZ (.kmz)**: KML compactado
- **GeoJSON (.geojson)**: Formato web padrão
- **GPX (.gpx)**: Formato de GPS

#### Como Enviar
1. **Arrastar e Soltar**: Arraste o arquivo diretamente para a área de upload
2. **Selecionar Arquivo**: Clique em "Selecionar Arquivo" e escolha no seu computador
3. **Aguardar Processamento**: O sistema processará automaticamente o arquivo

> **💡 Dica**: Para Shapefiles, você pode enviar apenas o arquivo .shp principal. O sistema processará automaticamente os arquivos auxiliares se estiverem na mesma pasta.

### 4. Configurando o Mapa

Na terceira etapa, personalize seu mapa:

#### Informações Básicas
- **Título do Mapa**: Aparecerá no topo do mapa
- **Subtítulo**: Informação adicional (opcional)
- **Layout**: Escolha o tipo de mapa (Localização é o padrão)

#### Personalização Visual
- **Cor Primária**: Cor principal dos elementos do mapa
- **Cor Secundária**: Cor de contorno e detalhes
- **Elementos do Mapa**:
  - ☑️ Escala
  - ☑️ Rosa dos Ventos
  - ☑️ Legenda

#### Informações Adicionais
- **Logo**: Envie o logo da sua empresa (opcional)
- **Informações Extras**: Texto adicional para o mapa

### 5. Finalizando o Projeto

Após configurar tudo, clique em **"Criar Projeto"**. Você será redirecionado para a página de detalhes do projeto.

## Gerenciando Projetos

### Visualizando Projetos

Na página **"Meus Projetos"**, você pode:
- Ver todos os seus projetos
- Buscar projetos por nome
- Filtrar por data de criação
- Acessar detalhes de cada projeto

### Detalhes do Projeto

Na página de detalhes, você encontra:

#### Informações Gerais
- Nome e descrição do projeto
- Data de criação e última atualização
- Estatísticas (arquivos enviados, mapas gerados)

#### Arquivos GIS
- Lista de todos os arquivos enviados
- Informações técnicas (tipo, tamanho, sistema de coordenadas)
- Opções para download ou exclusão

#### Mapas Gerados
- Histórico de mapas criados
- Status de cada geração
- Links para visualização e download

#### Configuração do Mapa
- Visualização das configurações atuais
- Opção para editar configurações

## Gerando Mapas

### Iniciando a Geração

1. Na página de detalhes do projeto, clique em **"Gerar Mapa"**
2. Escolha o formato desejado:
   - **HTML Interativo**: Para visualização online
   - **PNG Alta Qualidade**: Para apresentações e impressão
   - **PDF Profissional**: Para relatórios e documentos

### Formatos de Saída

#### 🌐 HTML Interativo
- **Uso**: Visualização online, sites, apresentações digitais
- **Características**: 
  - Zoom e navegação
  - Camadas interativas
  - Responsivo (adapta-se a diferentes telas)
- **Tamanho**: Pequeno (alguns KB)

#### 🖼️ PNG Alta Qualidade
- **Uso**: Apresentações, impressão, documentos
- **Características**:
  - Resolução 300 DPI
  - Qualidade profissional
  - Cores vibrantes
- **Tamanho**: Médio (alguns MB)

#### 📄 PDF Profissional
- **Uso**: Relatórios, documentos oficiais, arquivamento
- **Características**:
  - Layout profissional
  - Metadados incorporados
  - Pronto para impressão
- **Tamanho**: Médio (alguns MB)

### Tempo de Processamento

- **HTML**: 30 segundos - 2 minutos
- **PNG**: 1 - 3 minutos
- **PDF**: 2 - 5 minutos

> **⏱️ Nota**: O tempo varia conforme o tamanho e complexidade dos arquivos GIS.

## Tipos de Mapas

### Mapa de Localização (Padrão)

O mapa de localização é composto por:

#### Mapa Principal
- Área de interesse em destaque
- Maior área do mapa
- Detalhes da geometria enviada

#### Mapas de Contexto
- **Mapa Municipal**: Mostra a localização dentro do município
- **Mapa Estadual**: Mostra a localização dentro do estado
- Ajudam a situar geograficamente a área

#### Elementos Cartográficos
- **Escala**: Referência de distâncias
- **Rosa dos Ventos**: Orientação norte
- **Legenda**: Explicação dos símbolos
- **Título e Subtítulo**: Identificação do mapa

## Dicas e Boas Práticas

### 📁 Preparando Arquivos

#### Shapefiles
- Certifique-se de ter todos os arquivos (.shp, .dbf, .shx, .prj)
- Mantenha os arquivos na mesma pasta
- Use nomes sem espaços ou caracteres especiais

#### KML/KMZ
- Exporte do Google Earth ou software GIS
- Verifique se as geometrias estão corretas
- Evite arquivos muito complexos

#### Coordenadas
- Prefira sistemas de coordenadas conhecidos (WGS84, UTM)
- O sistema reprojetará automaticamente se necessário

### 🎨 Personalização

#### Cores
- Use cores contrastantes para boa visualização
- Considere a impressão em preto e branco
- Teste diferentes combinações

#### Títulos
- Seja descritivo mas conciso
- Use linguagem clara e profissional
- Evite abreviações desnecessárias

#### Logos
- Use imagens de alta qualidade (PNG ou JPG)
- Tamanho recomendado: 200x200 pixels
- Fundo transparente para melhor integração

### 📊 Qualidade dos Dados

#### Verificação
- Confira se as geometrias estão corretas
- Verifique o sistema de coordenadas
- Teste com uma pequena amostra primeiro

#### Simplificação
- Para áreas muito complexas, considere simplificar
- Remova detalhes desnecessários
- Mantenha apenas o essencial

## Solução de Problemas

### ❌ Problemas Comuns

#### "Arquivo não suportado"
- **Causa**: Formato de arquivo não reconhecido
- **Solução**: Converta para um formato suportado (SHP, KML, GeoJSON)

#### "Erro no processamento"
- **Causa**: Arquivo corrompido ou geometria inválida
- **Solução**: Verifique o arquivo em um software GIS antes do upload

#### "Mapa vazio"
- **Causa**: Sistema de coordenadas incorreto ou geometria fora dos limites
- **Solução**: Verifique o sistema de coordenadas do arquivo

#### "Geração muito lenta"
- **Causa**: Arquivo muito grande ou complexo
- **Solução**: Simplifique o arquivo ou divida em partes menores

### 🔧 Dicas de Resolução

1. **Sempre teste com arquivos pequenos primeiro**
2. **Verifique a integridade dos arquivos antes do upload**
3. **Use sistemas de coordenadas padrão quando possível**
4. **Mantenha backups dos arquivos originais**

## Limitações e Restrições

### Tamanhos de Arquivo
- **Máximo por arquivo**: 50 MB
- **Máximo por projeto**: 200 MB
- **Formatos de imagem para logo**: 5 MB

### Tipos de Geometria
- **Suportados**: Pontos, Linhas, Polígonos
- **Limitações**: Geometrias 3D são convertidas para 2D

### Sistemas de Coordenadas
- **Automático**: Reprojeção para WGS84
- **Suportados**: Principais sistemas mundiais
- **Limitação**: Sistemas locais podem não ser reconhecidos

## Exemplos Práticos

### Exemplo 1: Mapa de Propriedade Rural

**Objetivo**: Criar mapa de uma fazenda para relatório ambiental

**Passos**:
1. Criar projeto "Fazenda São João - Relatório Ambiental"
2. Upload do shapefile da propriedade
3. Configurar:
   - Título: "Propriedade Rural São João"
   - Subtítulo: "Município de Exemplo - Estado"
   - Cor primária: Verde (#228B22)
   - Adicionar logo da empresa
4. Gerar em PDF para o relatório

### Exemplo 2: Mapa de Localização Urbana

**Objetivo**: Mostrar localização de um empreendimento

**Passos**:
1. Criar projeto "Empreendimento Centro"
2. Upload do arquivo KML da área
3. Configurar:
   - Título: "Localização do Empreendimento"
   - Subtítulo: "Centro da Cidade"
   - Cor primária: Azul (#1E90FF)
   - Informações adicionais sobre acesso
4. Gerar em HTML para site

### Exemplo 3: Mapa de Trilha

**Objetivo**: Documentar trilha ecológica

**Passos**:
1. Criar projeto "Trilha Ecológica"
2. Upload do arquivo GPX da trilha
3. Configurar:
   - Título: "Trilha da Cachoeira"
   - Subtítulo: "Parque Nacional"
   - Cor primária: Verde escuro (#006400)
   - Adicionar informações sobre dificuldade
4. Gerar em PNG para folder turístico

## Suporte e Ajuda

### 📞 Canais de Suporte

- **Documentação**: Este guia e a documentação técnica
- **FAQ**: Perguntas frequentes na plataforma
- **Suporte Técnico**: Entre em contato através do formulário

### 🆘 Quando Solicitar Ajuda

- Problemas técnicos persistentes
- Dúvidas sobre funcionalidades
- Sugestões de melhorias
- Relatórios de bugs

### 📝 Informações para Suporte

Ao solicitar ajuda, inclua:
- Descrição detalhada do problema
- Passos para reproduzir o erro
- Tipo e tamanho do arquivo
- Navegador e sistema operacional
- Capturas de tela (se aplicável)

## Atualizações e Novidades

### 🔄 Histórico de Versões

A plataforma é constantemente atualizada com:
- Novos formatos de arquivo
- Melhorias de performance
- Correções de bugs
- Novas funcionalidades

### 🚀 Próximas Funcionalidades

- Mais tipos de mapas (hidrográfico, relevo)
- Colaboração em projetos
- Templates personalizados
- Integração com serviços de mapas

## Conclusão

O **GIS SaaS** foi desenvolvido para simplificar a criação de mapas profissionais, permitindo que você foque no seu trabalho principal enquanto a plataforma cuida da parte técnica da cartografia.

Com este guia, você tem todas as informações necessárias para aproveitar ao máximo a plataforma. Lembre-se de que a prática leva à perfeição - experimente com diferentes tipos de arquivos e configurações para descobrir o que funciona melhor para seus projetos.

**Bom mapeamento!** 🗺️✨

---

**Precisa de ajuda?** Entre em contato conosco através dos canais de suporte disponíveis na plataforma.

**Versão do Guia**: 1.0.0  
**Última Atualização**: Setembro 2025

