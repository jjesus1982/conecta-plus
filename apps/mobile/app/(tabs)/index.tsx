/**
 * Conecta Plus Mobile - Dashboard/Home
 * Tela principal com resumo e acesso rápido
 */

import React from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  RefreshControl,
  Image,
} from 'react-native';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useQuery } from '@tanstack/react-query';
import { LinearGradient } from 'expo-linear-gradient';
import { useAuthStore } from '../../src/stores/authStore';
import { dashboardApi, encomendasApi, comunicadosApi } from '../../src/services/api';

type IconName = React.ComponentProps<typeof Ionicons>['name'];

interface QuickAction {
  id: string;
  title: string;
  icon: IconName;
  color: string;
  route: string;
}

const quickActions: QuickAction[] = [
  { id: 'ocorrencia', title: 'Nova\nOcorrência', icon: 'alert-circle', color: '#ef4444', route: '/ocorrencias/nova' },
  { id: 'reserva', title: 'Nova\nReserva', icon: 'calendar', color: '#8b5cf6', route: '/reservas/nova' },
  { id: 'visitante', title: 'Autorizar\nVisitante', icon: 'person-add', color: '#10b981', route: '/acesso/visitante' },
  { id: 'cftv', title: 'Ver\nCâmeras', icon: 'videocam', color: '#3b82f6', route: '/cftv' },
];

export default function DashboardScreen() {
  const { user, condominio } = useAuthStore();

  const { data: stats, isLoading, refetch } = useQuery({
    queryKey: ['dashboard'],
    queryFn: async () => {
      const response = await dashboardApi.getStats();
      return response.data;
    },
  });

  const { data: encomendas } = useQuery({
    queryKey: ['encomendas-pendentes'],
    queryFn: async () => {
      const response = await encomendasApi.list({ status: 'pendente', limit: 5 });
      return response.data;
    },
  });

  const { data: comunicados } = useQuery({
    queryKey: ['comunicados-recentes'],
    queryFn: async () => {
      const response = await comunicadosApi.list({ limit: 3 });
      return response.data;
    },
  });

  const isStaff = user?.role && ['admin', 'sindico', 'gerente', 'porteiro'].includes(user.role);

  return (
    <ScrollView
      style={styles.container}
      refreshControl={<RefreshControl refreshing={isLoading} onRefresh={refetch} />}
    >
      {/* Header com saudação */}
      <LinearGradient colors={['#2563eb', '#1d4ed8']} style={styles.header}>
        <View style={styles.headerContent}>
          <View>
            <Text style={styles.greeting}>
              Olá, {user?.nome?.split(' ')[0] || 'Morador'}
            </Text>
            <Text style={styles.subGreeting}>
              {condominio?.nome || 'Bem-vindo ao Conecta Plus'}
            </Text>
          </View>
          <TouchableOpacity style={styles.avatarContainer}>
            {user?.avatar_url ? (
              <Image source={{ uri: user.avatar_url }} style={styles.avatar} />
            ) : (
              <View style={styles.avatarPlaceholder}>
                <Text style={styles.avatarText}>
                  {user?.nome?.charAt(0).toUpperCase() || 'U'}
                </Text>
              </View>
            )}
          </TouchableOpacity>
        </View>
      </LinearGradient>

      {/* Ações rápidas */}
      <View style={styles.quickActionsContainer}>
        <Text style={styles.sectionTitle}>Acesso Rápido</Text>
        <View style={styles.quickActions}>
          {quickActions.map((action) => (
            <TouchableOpacity
              key={action.id}
              style={styles.quickAction}
              onPress={() => router.push(action.route as any)}
            >
              <View style={[styles.quickActionIcon, { backgroundColor: action.color }]}>
                <Ionicons name={action.icon} size={24} color="#fff" />
              </View>
              <Text style={styles.quickActionText}>{action.title}</Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* Cards de Status */}
      {isStaff && (
        <View style={styles.statsContainer}>
          <Text style={styles.sectionTitle}>Resumo do Dia</Text>
          <View style={styles.statsGrid}>
            <View style={[styles.statCard, { backgroundColor: '#dbeafe' }]}>
              <Ionicons name="people" size={24} color="#2563eb" />
              <Text style={styles.statValue}>{stats?.acessos_hoje || 0}</Text>
              <Text style={styles.statLabel}>Acessos Hoje</Text>
            </View>
            <View style={[styles.statCard, { backgroundColor: '#fef3c7' }]}>
              <Ionicons name="alert-circle" size={24} color="#f59e0b" />
              <Text style={styles.statValue}>{stats?.ocorrencias_abertas || 0}</Text>
              <Text style={styles.statLabel}>Ocorrências</Text>
            </View>
            <View style={[styles.statCard, { backgroundColor: '#dcfce7' }]}>
              <Ionicons name="cube" size={24} color="#10b981" />
              <Text style={styles.statValue}>{encomendas?.length || 0}</Text>
              <Text style={styles.statLabel}>Encomendas</Text>
            </View>
            <View style={[styles.statCard, { backgroundColor: '#ede9fe' }]}>
              <Ionicons name="calendar" size={24} color="#8b5cf6" />
              <Text style={styles.statValue}>{stats?.reservas_hoje || 0}</Text>
              <Text style={styles.statLabel}>Reservas</Text>
            </View>
          </View>
        </View>
      )}

      {/* Comunicados Recentes */}
      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Comunicados</Text>
          <TouchableOpacity onPress={() => router.push('/comunicados')}>
            <Text style={styles.seeAll}>Ver todos</Text>
          </TouchableOpacity>
        </View>

        {comunicados?.length > 0 ? (
          comunicados.slice(0, 3).map((comunicado: any) => (
            <TouchableOpacity
              key={comunicado.id}
              style={styles.comunicadoCard}
              onPress={() => router.push(`/comunicados/${comunicado.id}`)}
            >
              <View style={styles.comunicadoIcon}>
                <Ionicons name="megaphone" size={20} color="#2563eb" />
              </View>
              <View style={styles.comunicadoContent}>
                <Text style={styles.comunicadoTitle} numberOfLines={1}>
                  {comunicado.titulo}
                </Text>
                <Text style={styles.comunicadoDate}>
                  {new Date(comunicado.created_at).toLocaleDateString('pt-BR')}
                </Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#9ca3af" />
            </TouchableOpacity>
          ))
        ) : (
          <View style={styles.emptyState}>
            <Ionicons name="megaphone-outline" size={48} color="#d1d5db" />
            <Text style={styles.emptyText}>Nenhum comunicado recente</Text>
          </View>
        )}
      </View>

      {/* Encomendas Pendentes */}
      {encomendas?.length > 0 && (
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Suas Encomendas</Text>
            <TouchableOpacity onPress={() => router.push('/encomendas')}>
              <Text style={styles.seeAll}>Ver todas</Text>
            </TouchableOpacity>
          </View>

          {encomendas.map((encomenda: any) => (
            <TouchableOpacity
              key={encomenda.id}
              style={styles.encomendaCard}
              onPress={() => router.push(`/encomendas/${encomenda.id}`)}
            >
              <View style={styles.encomendaIcon}>
                <Ionicons name="cube" size={20} color="#10b981" />
              </View>
              <View style={styles.encomendaContent}>
                <Text style={styles.encomendaTitle} numberOfLines={1}>
                  {encomenda.descricao || 'Encomenda'}
                </Text>
                <Text style={styles.encomendaDate}>
                  Recebida em {new Date(encomenda.received_at).toLocaleDateString('pt-BR')}
                </Text>
              </View>
              <View style={styles.encomendaBadge}>
                <Text style={styles.encomendaBadgeText}>Retirar</Text>
              </View>
            </TouchableOpacity>
          ))}
        </View>
      )}

      {/* Espaço no final */}
      <View style={{ height: 24 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f3f4f6',
  },
  header: {
    paddingTop: 20,
    paddingBottom: 24,
    paddingHorizontal: 20,
    borderBottomLeftRadius: 24,
    borderBottomRightRadius: 24,
  },
  headerContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  greeting: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
  },
  subGreeting: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.8)',
    marginTop: 4,
  },
  avatarContainer: {
    width: 48,
    height: 48,
    borderRadius: 24,
    overflow: 'hidden',
  },
  avatar: {
    width: '100%',
    height: '100%',
  },
  avatarPlaceholder: {
    width: '100%',
    height: '100%',
    backgroundColor: 'rgba(255,255,255,0.2)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarText: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
  },
  quickActionsContainer: {
    marginTop: -12,
    paddingHorizontal: 20,
  },
  quickActions: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4,
  },
  quickAction: {
    alignItems: 'center',
    flex: 1,
  },
  quickActionIcon: {
    width: 48,
    height: 48,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 8,
  },
  quickActionText: {
    fontSize: 11,
    color: '#4b5563',
    textAlign: 'center',
    lineHeight: 14,
  },
  statsContainer: {
    marginTop: 24,
    paddingHorizontal: 20,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1f2937',
    marginBottom: 12,
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  statCard: {
    width: '48%',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
  },
  statValue: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#1f2937',
    marginTop: 8,
  },
  statLabel: {
    fontSize: 12,
    color: '#6b7280',
    marginTop: 4,
  },
  section: {
    marginTop: 24,
    paddingHorizontal: 20,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  seeAll: {
    fontSize: 14,
    color: '#2563eb',
    fontWeight: '500',
  },
  comunicadoCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 12,
    marginBottom: 8,
  },
  comunicadoIcon: {
    width: 40,
    height: 40,
    borderRadius: 10,
    backgroundColor: '#dbeafe',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  comunicadoContent: {
    flex: 1,
  },
  comunicadoTitle: {
    fontSize: 14,
    fontWeight: '500',
    color: '#1f2937',
  },
  comunicadoDate: {
    fontSize: 12,
    color: '#9ca3af',
    marginTop: 2,
  },
  encomendaCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 12,
    marginBottom: 8,
  },
  encomendaIcon: {
    width: 40,
    height: 40,
    borderRadius: 10,
    backgroundColor: '#dcfce7',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  encomendaContent: {
    flex: 1,
  },
  encomendaTitle: {
    fontSize: 14,
    fontWeight: '500',
    color: '#1f2937',
  },
  encomendaDate: {
    fontSize: 12,
    color: '#9ca3af',
    marginTop: 2,
  },
  encomendaBadge: {
    backgroundColor: '#10b981',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 8,
  },
  encomendaBadgeText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '500',
  },
  emptyState: {
    alignItems: 'center',
    padding: 24,
    backgroundColor: '#fff',
    borderRadius: 12,
  },
  emptyText: {
    color: '#9ca3af',
    marginTop: 8,
  },
});
