/**
 * Conecta Plus Mobile - Tab Layout
 * Navegação principal do app com bottom tabs
 */

import React from 'react';
import { Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Platform, View, Text, StyleSheet } from 'react-native';
import { useAuthStore } from '../../src/stores/authStore';

type IconName = React.ComponentProps<typeof Ionicons>['name'];

export default function TabLayout() {
  const { user, condominio } = useAuthStore();

  // Definir tabs baseado no role do usuário
  const isStaff = user?.role && ['admin', 'sindico', 'gerente', 'porteiro'].includes(user.role);

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: '#2563eb',
        tabBarInactiveTintColor: '#9ca3af',
        tabBarStyle: {
          backgroundColor: '#fff',
          borderTopWidth: 1,
          borderTopColor: '#e5e7eb',
          paddingBottom: Platform.OS === 'ios' ? 20 : 8,
          paddingTop: 8,
          height: Platform.OS === 'ios' ? 88 : 64,
        },
        tabBarLabelStyle: {
          fontSize: 11,
          fontWeight: '500',
        },
        headerStyle: {
          backgroundColor: '#2563eb',
        },
        headerTintColor: '#fff',
        headerTitleStyle: {
          fontWeight: '600',
        },
        headerRight: () => (
          <View style={styles.headerRight}>
            <Ionicons name="notifications-outline" size={24} color="#fff" />
          </View>
        ),
      }}
    >
      {/* Home/Dashboard */}
      <Tabs.Screen
        name="index"
        options={{
          title: 'Início',
          headerTitle: condominio?.nome || 'Conecta Plus',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="home-outline" size={size} color={color} />
          ),
        }}
      />

      {/* CFTV - Apenas staff */}
      {isStaff && (
        <Tabs.Screen
          name="cftv"
          options={{
            title: 'CFTV',
            tabBarIcon: ({ color, size }) => (
              <Ionicons name="videocam-outline" size={size} color={color} />
            ),
          }}
        />
      )}

      {/* Acesso - Apenas staff */}
      {isStaff && (
        <Tabs.Screen
          name="acesso"
          options={{
            title: 'Acesso',
            tabBarIcon: ({ color, size }) => (
              <Ionicons name="key-outline" size={size} color={color} />
            ),
          }}
        />
      )}

      {/* Ocorrências */}
      <Tabs.Screen
        name="ocorrencias"
        options={{
          title: 'Ocorrências',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="alert-circle-outline" size={size} color={color} />
          ),
        }}
      />

      {/* Reservas */}
      <Tabs.Screen
        name="reservas"
        options={{
          title: 'Reservas',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="calendar-outline" size={size} color={color} />
          ),
        }}
      />

      {/* Comunicados */}
      <Tabs.Screen
        name="comunicados"
        options={{
          title: 'Avisos',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="megaphone-outline" size={size} color={color} />
          ),
        }}
      />

      {/* Financeiro */}
      <Tabs.Screen
        name="financeiro"
        options={{
          title: 'Financeiro',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="wallet-outline" size={size} color={color} />
          ),
        }}
      />

      {/* Encomendas */}
      <Tabs.Screen
        name="encomendas"
        options={{
          title: 'Encomendas',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="cube-outline" size={size} color={color} />
          ),
        }}
      />

      {/* Menu/Perfil */}
      <Tabs.Screen
        name="perfil"
        options={{
          title: 'Perfil',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="person-outline" size={size} color={color} />
          ),
        }}
      />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  headerRight: {
    marginRight: 16,
  },
});
