/**
 * Conecta Plus Mobile - Tela de Perfil
 * Configurações e informações do usuário
 */

import React from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  Image,
  Alert,
  Switch,
} from 'react-native';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuthStore } from '../../src/stores/authStore';

type IconName = React.ComponentProps<typeof Ionicons>['name'];

interface MenuItem {
  id: string;
  title: string;
  subtitle?: string;
  icon: IconName;
  color: string;
  action?: () => void;
  route?: string;
  isSwitch?: boolean;
  value?: boolean;
}

export default function PerfilScreen() {
  const { user, condominio, logout } = useAuthStore();
  const [notificationsEnabled, setNotificationsEnabled] = React.useState(true);
  const [biometricEnabled, setBiometricEnabled] = React.useState(false);

  const handleLogout = () => {
    Alert.alert(
      'Sair',
      'Deseja realmente sair da sua conta?',
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Sair',
          style: 'destructive',
          onPress: async () => {
            await logout();
            router.replace('/(auth)/login');
          },
        },
      ]
    );
  };

  const menuItems: MenuItem[][] = [
    // Conta
    [
      {
        id: 'edit-profile',
        title: 'Editar Perfil',
        subtitle: 'Alterar nome, foto e dados pessoais',
        icon: 'person-outline',
        color: '#2563eb',
        route: '/configuracoes/perfil',
      },
      {
        id: 'change-password',
        title: 'Alterar Senha',
        subtitle: 'Atualizar sua senha de acesso',
        icon: 'lock-closed-outline',
        color: '#8b5cf6',
        route: '/configuracoes/senha',
      },
    ],
    // Preferências
    [
      {
        id: 'notifications',
        title: 'Notificações',
        subtitle: 'Receber alertas e avisos',
        icon: 'notifications-outline',
        color: '#f59e0b',
        isSwitch: true,
        value: notificationsEnabled,
        action: () => setNotificationsEnabled(!notificationsEnabled),
      },
      {
        id: 'biometric',
        title: 'Login Biométrico',
        subtitle: 'Face ID / Impressão digital',
        icon: 'finger-print-outline',
        color: '#10b981',
        isSwitch: true,
        value: biometricEnabled,
        action: () => setBiometricEnabled(!biometricEnabled),
      },
    ],
    // Suporte
    [
      {
        id: 'help',
        title: 'Central de Ajuda',
        icon: 'help-circle-outline',
        color: '#6b7280',
        route: '/configuracoes/ajuda',
      },
      {
        id: 'contact',
        title: 'Fale Conosco',
        icon: 'chatbubbles-outline',
        color: '#6b7280',
        route: '/configuracoes/contato',
      },
      {
        id: 'about',
        title: 'Sobre o App',
        subtitle: 'Versão 1.0.0',
        icon: 'information-circle-outline',
        color: '#6b7280',
        route: '/configuracoes/sobre',
      },
    ],
  ];

  const getRoleLabel = (role: string) => {
    const roles: Record<string, string> = {
      admin: 'Administrador',
      sindico: 'Síndico',
      gerente: 'Gerente',
      porteiro: 'Porteiro',
      morador: 'Morador',
      visitante: 'Visitante',
    };
    return roles[role] || role;
  };

  return (
    <ScrollView style={styles.container}>
      {/* Header do Perfil */}
      <View style={styles.header}>
        <View style={styles.avatarContainer}>
          {user?.avatar_url ? (
            <Image source={{ uri: user.avatar_url }} style={styles.avatar} />
          ) : (
            <View style={styles.avatarPlaceholder}>
              <Text style={styles.avatarText}>
                {user?.nome?.charAt(0).toUpperCase() || 'U'}
              </Text>
            </View>
          )}
          <TouchableOpacity style={styles.editAvatarButton}>
            <Ionicons name="camera" size={16} color="#fff" />
          </TouchableOpacity>
        </View>

        <Text style={styles.userName}>{user?.nome || 'Usuário'}</Text>
        <Text style={styles.userEmail}>{user?.email}</Text>

        <View style={styles.roleContainer}>
          <View style={styles.roleBadge}>
            <Ionicons name="shield-checkmark" size={14} color="#2563eb" />
            <Text style={styles.roleText}>{getRoleLabel(user?.role || 'morador')}</Text>
          </View>
        </View>

        {condominio && (
          <View style={styles.condominioInfo}>
            <Ionicons name="business-outline" size={16} color="#6b7280" />
            <Text style={styles.condominioText}>{condominio.nome}</Text>
          </View>
        )}
      </View>

      {/* Menu de Opções */}
      {menuItems.map((section, sectionIndex) => (
        <View key={sectionIndex} style={styles.section}>
          {section.map((item, itemIndex) => (
            <TouchableOpacity
              key={item.id}
              style={[
                styles.menuItem,
                itemIndex === 0 && styles.menuItemFirst,
                itemIndex === section.length - 1 && styles.menuItemLast,
              ]}
              onPress={item.action || (() => item.route && router.push(item.route as any))}
              disabled={item.isSwitch}
            >
              <View style={[styles.menuIcon, { backgroundColor: `${item.color}20` }]}>
                <Ionicons name={item.icon} size={20} color={item.color} />
              </View>

              <View style={styles.menuContent}>
                <Text style={styles.menuTitle}>{item.title}</Text>
                {item.subtitle && (
                  <Text style={styles.menuSubtitle}>{item.subtitle}</Text>
                )}
              </View>

              {item.isSwitch ? (
                <Switch
                  value={item.value}
                  onValueChange={item.action}
                  trackColor={{ false: '#e5e7eb', true: '#93c5fd' }}
                  thumbColor={item.value ? '#2563eb' : '#f4f4f5'}
                />
              ) : (
                <Ionicons name="chevron-forward" size={20} color="#9ca3af" />
              )}
            </TouchableOpacity>
          ))}
        </View>
      ))}

      {/* Botão de Logout */}
      <View style={styles.section}>
        <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
          <Ionicons name="log-out-outline" size={20} color="#ef4444" />
          <Text style={styles.logoutText}>Sair da Conta</Text>
        </TouchableOpacity>
      </View>

      {/* Footer */}
      <View style={styles.footer}>
        <Text style={styles.footerText}>Conecta Plus v1.0.0</Text>
        <Text style={styles.footerText}>Todos os direitos reservados</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f3f4f6',
  },
  header: {
    alignItems: 'center',
    paddingVertical: 32,
    paddingHorizontal: 24,
    backgroundColor: '#fff',
    borderBottomLeftRadius: 24,
    borderBottomRightRadius: 24,
    marginBottom: 16,
  },
  avatarContainer: {
    position: 'relative',
    marginBottom: 16,
  },
  avatar: {
    width: 96,
    height: 96,
    borderRadius: 48,
  },
  avatarPlaceholder: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: '#2563eb',
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarText: {
    fontSize: 36,
    fontWeight: 'bold',
    color: '#fff',
  },
  editAvatarButton: {
    position: 'absolute',
    bottom: 0,
    right: 0,
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#2563eb',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 3,
    borderColor: '#fff',
  },
  userName: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#1f2937',
  },
  userEmail: {
    fontSize: 14,
    color: '#6b7280',
    marginTop: 4,
  },
  roleContainer: {
    marginTop: 12,
  },
  roleBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#dbeafe',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    gap: 6,
  },
  roleText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#2563eb',
  },
  condominioInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 12,
    gap: 6,
  },
  condominioText: {
    fontSize: 14,
    color: '#6b7280',
  },
  section: {
    marginHorizontal: 16,
    marginBottom: 16,
    backgroundColor: '#fff',
    borderRadius: 16,
    overflow: 'hidden',
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#f3f4f6',
  },
  menuItemFirst: {
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
  },
  menuItemLast: {
    borderBottomWidth: 0,
    borderBottomLeftRadius: 16,
    borderBottomRightRadius: 16,
  },
  menuIcon: {
    width: 40,
    height: 40,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  menuContent: {
    flex: 1,
  },
  menuTitle: {
    fontSize: 16,
    fontWeight: '500',
    color: '#1f2937',
  },
  menuSubtitle: {
    fontSize: 12,
    color: '#6b7280',
    marginTop: 2,
  },
  logoutButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    gap: 8,
  },
  logoutText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#ef4444',
  },
  footer: {
    alignItems: 'center',
    paddingVertical: 24,
  },
  footerText: {
    fontSize: 12,
    color: '#9ca3af',
  },
});
