/**
 * Conecta Plus Mobile - Root Layout
 * Configuração principal do app com providers e navegação
 */

import { useEffect } from 'react';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import * as SplashScreen from 'expo-splash-screen';
import * as Notifications from 'expo-notifications';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { useAuthStore } from '../src/stores/authStore';

// Manter splash screen visível enquanto carrega recursos
SplashScreen.preventAutoHideAsync();

// Configurar handler de notificações
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

// Query client para React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutos
      gcTime: 1000 * 60 * 30, // 30 minutos
      retry: 2,
    },
  },
});

export default function RootLayout() {
  const { isAuthenticated, loadStoredAuth } = useAuthStore();

  useEffect(() => {
    async function prepare() {
      try {
        // Carregar autenticação armazenada
        await loadStoredAuth();

        // Registrar para push notifications
        await registerForPushNotifications();
      } catch (e) {
        console.warn('Erro ao preparar app:', e);
      } finally {
        // Esconder splash screen
        await SplashScreen.hideAsync();
      }
    }

    prepare();
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <GestureHandlerRootView style={{ flex: 1 }}>
        <StatusBar style="auto" />
        <Stack screenOptions={{ headerShown: false }}>
          <Stack.Screen name="(auth)" options={{ headerShown: false }} />
          <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
          <Stack.Screen
            name="cftv/[camera]"
            options={{
              headerShown: true,
              title: 'CFTV',
              presentation: 'modal'
            }}
          />
          <Stack.Screen
            name="ocorrencias/nova"
            options={{
              headerShown: true,
              title: 'Nova Ocorrência',
              presentation: 'modal'
            }}
          />
          <Stack.Screen
            name="reservas/nova"
            options={{
              headerShown: true,
              title: 'Nova Reserva',
              presentation: 'modal'
            }}
          />
        </Stack>
      </GestureHandlerRootView>
    </QueryClientProvider>
  );
}

async function registerForPushNotifications() {
  try {
    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;

    if (existingStatus !== 'granted') {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }

    if (finalStatus !== 'granted') {
      console.log('Permissão para notificações não concedida');
      return;
    }

    const token = await Notifications.getExpoPushTokenAsync();
    console.log('Push token:', token.data);

    // Enviar token para o backend
    await sendPushTokenToBackend(token.data);

    return token.data;
  } catch (error) {
    console.error('Erro ao registrar notificações:', error);
  }
}

/**
 * Envia o push token para o backend para registro de notificações
 */
async function sendPushTokenToBackend(pushToken: string) {
  try {
    const { default: AsyncStorage } = await import('@react-native-async-storage/async-storage');
    const authToken = await AsyncStorage.getItem('conecta_plus_token');

    if (!authToken) {
      // Usuário não está logado, salvar token para enviar após login
      await AsyncStorage.setItem('pending_push_token', pushToken);
      return;
    }

    const response = await fetch(`${process.env.EXPO_PUBLIC_API_URL}/api/v1/usuarios/push-token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`,
      },
      body: JSON.stringify({
        push_token: pushToken,
        platform: 'expo',
        device_info: {
          brand: 'expo',
          model: 'mobile',
        },
      }),
    });

    if (response.ok) {
      console.log('Push token registrado com sucesso no backend');
      await AsyncStorage.removeItem('pending_push_token');
    } else {
      console.warn('Falha ao registrar push token:', response.status);
    }
  } catch (error) {
    console.error('Erro ao enviar push token para backend:', error);
  }
}
