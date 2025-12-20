/**
 * Conecta Plus Mobile - Tela de CFTV
 * Visualização de câmeras integradas com Frigate NVR
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  RefreshControl,
  Image,
  Dimensions,
} from 'react-native';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useQuery } from '@tanstack/react-query';
import { frigateApi, cftvApi } from '../../src/services/api';

const { width } = Dimensions.get('window');
const cardWidth = (width - 48) / 2;

interface Camera {
  name: string;
  enabled: boolean;
  detect_enabled: boolean;
  record_enabled: boolean;
  snapshots_enabled: boolean;
}

interface FrigateInstance {
  id: string;
  name: string;
  url: string;
}

export default function CFTVScreen() {
  const [selectedInstance, setSelectedInstance] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  // Buscar instâncias Frigate
  const { data: instances, refetch: refetchInstances } = useQuery({
    queryKey: ['frigate-instances'],
    queryFn: async () => {
      const response = await frigateApi.listInstances();
      return response.data as FrigateInstance[];
    },
  });

  // Selecionar primeira instância automaticamente
  React.useEffect(() => {
    if (instances?.length && !selectedInstance) {
      setSelectedInstance(instances[0].id);
    }
  }, [instances]);

  // Buscar câmeras da instância selecionada
  const { data: cameras, refetch: refetchCameras, isLoading } = useQuery({
    queryKey: ['frigate-cameras', selectedInstance],
    queryFn: async () => {
      if (!selectedInstance) return [];
      const response = await frigateApi.listCameras(selectedInstance);
      return response.data as Camera[];
    },
    enabled: !!selectedInstance,
  });

  // Buscar eventos recentes
  const { data: events } = useQuery({
    queryKey: ['frigate-events', selectedInstance],
    queryFn: async () => {
      if (!selectedInstance) return [];
      const response = await frigateApi.getEvents(selectedInstance, {
        limit: 10,
        has_snapshot: true,
      });
      return response.data.events;
    },
    enabled: !!selectedInstance,
    refetchInterval: 30000, // Atualizar a cada 30 segundos
  });

  const handleRefresh = async () => {
    setRefreshing(true);
    await Promise.all([refetchInstances(), refetchCameras()]);
    setRefreshing(false);
  };

  const getSnapshotUrl = (camera: string) => {
    if (!selectedInstance || !instances) return null;
    const instance = instances.find((i) => i.id === selectedInstance);
    if (!instance) return null;
    return `${instance.url}/api/${camera}/latest.jpg?h=480`;
  };

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing || isLoading} onRefresh={handleRefresh} />
      }
    >
      {/* Seletor de Instância */}
      {instances && instances.length > 1 && (
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.instanceSelector}
        >
          {instances.map((instance) => (
            <TouchableOpacity
              key={instance.id}
              style={[
                styles.instanceChip,
                selectedInstance === instance.id && styles.instanceChipActive,
              ]}
              onPress={() => setSelectedInstance(instance.id)}
            >
              <Text
                style={[
                  styles.instanceChipText,
                  selectedInstance === instance.id && styles.instanceChipTextActive,
                ]}
              >
                {instance.name}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      )}

      {/* Grid de Câmeras */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Câmeras ao Vivo</Text>

        {cameras && cameras.length > 0 ? (
          <View style={styles.cameraGrid}>
            {cameras.map((camera) => (
              <TouchableOpacity
                key={camera.name}
                style={styles.cameraCard}
                onPress={() =>
                  router.push({
                    pathname: '/cftv/[camera]',
                    params: { camera: camera.name, instance: selectedInstance },
                  })
                }
              >
                <View style={styles.cameraPreview}>
                  <Image
                    source={{ uri: getSnapshotUrl(camera.name) || undefined }}
                    style={styles.cameraImage}
                    resizeMode="cover"
                  />
                  <View style={styles.cameraOverlay}>
                    <Ionicons name="play-circle" size={32} color="#fff" />
                  </View>

                  {/* Status badges */}
                  <View style={styles.cameraBadges}>
                    {camera.record_enabled && (
                      <View style={[styles.badge, styles.badgeRed]}>
                        <View style={styles.recordDot} />
                        <Text style={styles.badgeText}>REC</Text>
                      </View>
                    )}
                    {camera.detect_enabled && (
                      <View style={[styles.badge, styles.badgeGreen]}>
                        <Ionicons name="eye" size={10} color="#fff" />
                      </View>
                    )}
                  </View>
                </View>

                <View style={styles.cameraInfo}>
                  <Text style={styles.cameraName} numberOfLines={1}>
                    {camera.name}
                  </Text>
                  <View style={styles.cameraStatus}>
                    <View
                      style={[
                        styles.statusDot,
                        camera.enabled ? styles.statusOnline : styles.statusOffline,
                      ]}
                    />
                    <Text style={styles.statusText}>
                      {camera.enabled ? 'Online' : 'Offline'}
                    </Text>
                  </View>
                </View>
              </TouchableOpacity>
            ))}
          </View>
        ) : (
          <View style={styles.emptyState}>
            <Ionicons name="videocam-off-outline" size={64} color="#d1d5db" />
            <Text style={styles.emptyTitle}>Nenhuma câmera encontrada</Text>
            <Text style={styles.emptyText}>
              Configure câmeras no Frigate NVR para visualizar aqui
            </Text>
          </View>
        )}
      </View>

      {/* Eventos Recentes */}
      {events && events.length > 0 && (
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Detecções Recentes</Text>
            <TouchableOpacity>
              <Text style={styles.seeAll}>Ver todas</Text>
            </TouchableOpacity>
          </View>

          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.eventsScroll}
          >
            {events.map((event: any) => (
              <TouchableOpacity key={event.id} style={styles.eventCard}>
                <Image
                  source={{ uri: event.thumbnail_url }}
                  style={styles.eventImage}
                  resizeMode="cover"
                />
                <View style={styles.eventInfo}>
                  <View style={styles.eventLabel}>
                    <Ionicons
                      name={event.label === 'person' ? 'person' : 'car'}
                      size={12}
                      color="#fff"
                    />
                    <Text style={styles.eventLabelText}>{event.label}</Text>
                  </View>
                  <Text style={styles.eventCamera}>{event.camera}</Text>
                  <Text style={styles.eventTime}>
                    {new Date(event.start_time * 1000).toLocaleTimeString('pt-BR', {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </Text>
                </View>
              </TouchableOpacity>
            ))}
          </ScrollView>
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
  instanceSelector: {
    padding: 16,
    gap: 8,
  },
  instanceChip: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: '#fff',
    borderRadius: 20,
    marginRight: 8,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  instanceChipActive: {
    backgroundColor: '#2563eb',
    borderColor: '#2563eb',
  },
  instanceChipText: {
    color: '#4b5563',
    fontWeight: '500',
  },
  instanceChipTextActive: {
    color: '#fff',
  },
  section: {
    padding: 16,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1f2937',
    marginBottom: 12,
  },
  seeAll: {
    fontSize: 14,
    color: '#2563eb',
    fontWeight: '500',
  },
  cameraGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  cameraCard: {
    width: cardWidth,
    backgroundColor: '#fff',
    borderRadius: 12,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  cameraPreview: {
    width: '100%',
    aspectRatio: 16 / 9,
    backgroundColor: '#1f2937',
    position: 'relative',
  },
  cameraImage: {
    width: '100%',
    height: '100%',
  },
  cameraOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.3)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  cameraBadges: {
    position: 'absolute',
    top: 8,
    right: 8,
    flexDirection: 'row',
    gap: 4,
  },
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    gap: 4,
  },
  badgeRed: {
    backgroundColor: '#ef4444',
  },
  badgeGreen: {
    backgroundColor: '#10b981',
  },
  badgeText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: '600',
  },
  recordDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#fff',
  },
  cameraInfo: {
    padding: 12,
  },
  cameraName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#1f2937',
  },
  cameraStatus: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 4,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 6,
  },
  statusOnline: {
    backgroundColor: '#10b981',
  },
  statusOffline: {
    backgroundColor: '#ef4444',
  },
  statusText: {
    fontSize: 12,
    color: '#6b7280',
  },
  emptyState: {
    alignItems: 'center',
    padding: 48,
    backgroundColor: '#fff',
    borderRadius: 16,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1f2937',
    marginTop: 16,
  },
  emptyText: {
    fontSize: 14,
    color: '#6b7280',
    textAlign: 'center',
    marginTop: 8,
  },
  eventsScroll: {
    gap: 12,
  },
  eventCard: {
    width: 120,
    backgroundColor: '#fff',
    borderRadius: 12,
    overflow: 'hidden',
    marginRight: 12,
  },
  eventImage: {
    width: '100%',
    height: 80,
    backgroundColor: '#1f2937',
  },
  eventInfo: {
    padding: 8,
  },
  eventLabel: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#2563eb',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    alignSelf: 'flex-start',
    gap: 4,
    marginBottom: 4,
  },
  eventLabelText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: '600',
    textTransform: 'capitalize',
  },
  eventCamera: {
    fontSize: 12,
    fontWeight: '500',
    color: '#1f2937',
  },
  eventTime: {
    fontSize: 11,
    color: '#6b7280',
  },
});
