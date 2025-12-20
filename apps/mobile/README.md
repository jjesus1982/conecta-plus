# Conecta Plus Mobile

Aplicativo mobile nativo para o sistema Conecta Plus, desenvolvido com React Native e Expo.

## Tecnologias

- **React Native** - Framework de desenvolvimento mobile
- **Expo** - Plataforma de desenvolvimento e build
- **Expo Router** - Navegação file-based
- **TypeScript** - Tipagem estática
- **Zustand** - Gerenciamento de estado
- **React Query** - Cache e sincronização de dados
- **Axios** - Cliente HTTP

## Estrutura do Projeto

```
apps/mobile/
├── app/                    # Rotas (Expo Router)
│   ├── (auth)/            # Telas de autenticação
│   │   └── login.tsx
│   ├── (tabs)/            # Tabs principais
│   │   ├── _layout.tsx
│   │   ├── index.tsx      # Dashboard
│   │   ├── cftv.tsx       # CFTV/Câmeras
│   │   ├── acesso.tsx     # Controle de acesso
│   │   ├── ocorrencias.tsx
│   │   ├── reservas.tsx
│   │   ├── comunicados.tsx
│   │   ├── financeiro.tsx
│   │   ├── encomendas.tsx
│   │   └── perfil.tsx
│   ├── cftv/              # Telas de CFTV
│   ├── ocorrencias/       # Telas de ocorrências
│   └── _layout.tsx        # Layout raiz
├── src/
│   ├── components/        # Componentes reutilizáveis
│   ├── hooks/             # Custom hooks
│   ├── services/          # API e serviços
│   ├── stores/            # Zustand stores
│   └── utils/             # Utilitários
├── app.json               # Configuração Expo
├── package.json
└── tsconfig.json
```

## Instalação

```bash
# Instalar dependências
npm install

# Iniciar em modo desenvolvimento
npm start

# Build para Android
npm run build:android

# Build para iOS
npm run build:ios
```

## Configuração

### Variáveis de Ambiente

Crie um arquivo `.env` na raiz:

```env
EXPO_PUBLIC_API_URL=http://localhost:8000/api/v1
```

### Configuração OAuth

Para login com Google/Microsoft, configure no `app.json`:

```json
{
  "expo": {
    "scheme": "conectaplus",
    "extra": {
      "googleClientId": "seu-client-id",
      "microsoftClientId": "seu-client-id"
    }
  }
}
```

## Features

### Autenticação
- Login com email/senha
- Login com Google (OAuth)
- Login com Microsoft (Azure AD)
- Login corporativo (LDAP/AD)
- Biometria (Face ID / Touch ID)
- Token refresh automático

### Dashboard
- Resumo do condomínio
- Ações rápidas
- Comunicados recentes
- Encomendas pendentes
- Estatísticas (staff)

### CFTV
- Visualização de câmeras ao vivo
- Integração com Frigate NVR
- Detecções de objetos (IA)
- Playback de gravações
- Controle PTZ

### Acesso
- Registro de entradas/saídas
- Autorização de visitantes
- QR Code para acesso
- Histórico de acessos

### Ocorrências
- Registro de ocorrências
- Anexar fotos
- Acompanhamento de status
- Comentários

### Reservas
- Agendamento de áreas comuns
- Verificação de disponibilidade
- Cancelamento

### Financeiro
- Visualização de boletos
- Código PIX para pagamento
- Extrato

### Notificações Push
- Alertas de visitantes
- Encomendas chegando
- Comunicados importantes
- Ocorrências atualizadas

## Build & Deploy

### EAS Build

```bash
# Instalar EAS CLI
npm install -g eas-cli

# Login
eas login

# Configurar projeto
eas build:configure

# Build de desenvolvimento
eas build --profile development --platform android

# Build de produção
eas build --profile production --platform all

# Submit para stores
eas submit --platform android
eas submit --platform ios
```

## Licença

Proprietário - Conecta Plus
