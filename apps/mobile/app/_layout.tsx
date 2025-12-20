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

    // TODO: Enviar token para o backend
    return token.data;
  } catch (error) {
    console.error('Erro ao registrar notificações:', error);
  }
}
