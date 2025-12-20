/**
 * Conecta Plus Mobile - Tela de Login
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  ActivityIndicator,
  Alert,
  Image,
} from 'react-native';
import { router } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { useAuthStore } from '../../src/stores/authStore';
import { authApi } from '../../src/services/api';

interface SSOConfig {
  google_enabled: boolean;
  microsoft_enabled: boolean;
  ldap_enabled: boolean;
}

export default function LoginScreen() {
  const { login, loginWithGoogle, loginWithMicrosoft, loginWithLDAP, isLoading, isAuthenticated } = useAuthStore();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [ssoConfig, setSsoConfig] = useState<SSOConfig | null>(null);
  const [showLdapForm, setShowLdapForm] = useState(false);
  const [ldapUsername, setLdapUsername] = useState('');
  const [ldapPassword, setLdapPassword] = useState('');
  const [ldapDomain, setLdapDomain] = useState('');

  useEffect(() => {
    if (isAuthenticated) {
      router.replace('/(tabs)');
    }
  }, [isAuthenticated]);

  useEffect(() => {
    loadSSOConfig();
  }, []);

  const loadSSOConfig = async () => {
    try {
      const response = await authApi.ssoConfig();
      setSsoConfig(response.data);
    } catch (e) {
      console.log('SSO config não disponível');
    }
  };

  const handleLogin = async () => {
    if (!email || !password) {
      setError('Preencha todos os campos');
      return;
    }

    setError('');

    try {
      await login(email, password);
      router.replace('/(tabs)');
    } catch (err: any) {
      setError(err.message || 'Erro ao fazer login');
    }
  };

  const handleGoogleLogin = async () => {
    try {
      const authUrl = await loginWithGoogle();
      // TODO: Abrir WebView ou navegador para OAuth
      Alert.alert('Google Login', 'OAuth via navegador será implementado');
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleMicrosoftLogin = async () => {
    try {
      const authUrl = await loginWithMicrosoft();
      Alert.alert('Microsoft Login', 'OAuth via navegador será implementado');
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleLdapLogin = async () => {
    if (!ldapUsername || !ldapPassword) {
      setError('Preencha usuário e senha');
      return;
    }

    setError('');

    try {
      await loginWithLDAP(ldapUsername, ldapPassword, ldapDomain || undefined);
      router.replace('/(tabs)');
    } catch (err: any) {
      setError(err.message || 'Credenciais inválidas');
    }
  };

  return (
    <LinearGradient colors={['#2563eb', '#1e40af']} style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.keyboardView}
      >
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
        >
          {/* Logo */}
          <View style={styles.logoContainer}>
            <View style={styles.logoIcon}>
              <Ionicons name="business" size={48} color="#2563eb" />
            </View>
            <Text style={styles.logoText}>Conecta Plus</Text>
            <Text style={styles.tagline}>Gestão inteligente para seu condomínio</Text>
          </View>

          {/* Card de Login */}
          <View style={styles.card}>
            <Text style={styles.title}>Bem-vindo</Text>
            <Text style={styles.subtitle}>Entre com suas credenciais</Text>

            {error ? (
              <View style={styles.errorContainer}>
                <Ionicons name="alert-circle" size={20} color="#ef4444" />
                <Text style={styles.errorText}>{error}</Text>
              </View>
            ) : null}

            {/* Botões SSO */}
            {ssoConfig && (ssoConfig.google_enabled || ssoConfig.microsoft_enabled || ssoConfig.ldap_enabled) && (
              <View style={styles.ssoContainer}>
                {ssoConfig.google_enabled && (
                  <TouchableOpacity style={styles.ssoButton} onPress={handleGoogleLogin}>
                    <Ionicons name="logo-google" size={20} color="#4285F4" />
                    <Text style={styles.ssoButtonText}>Google</Text>
                  </TouchableOpacity>
                )}

                {ssoConfig.microsoft_enabled && (
                  <TouchableOpacity style={styles.ssoButton} onPress={handleMicrosoftLogin}>
                    <Ionicons name="logo-microsoft" size={20} color="#00A4EF" />
                    <Text style={styles.ssoButtonText}>Microsoft</Text>
                  </TouchableOpacity>
                )}

                {ssoConfig.ldap_enabled && (
                  <TouchableOpacity
                    style={styles.ssoButton}
                    onPress={() => setShowLdapForm(!showLdapForm)}
                  >
                    <Ionicons name="server" size={20} color="#6b7280" />
                    <Text style={styles.ssoButtonText}>AD/LDAP</Text>
                  </TouchableOpacity>
                )}

                {showLdapForm && ssoConfig.ldap_enabled && (
                  <View style={styles.ldapForm}>
                    <TextInput
                      style={styles.input}
                      placeholder="Usuário"
                      value={ldapUsername}
                      onChangeText={setLdapUsername}
                      autoCapitalize="none"
                    />
                    <TextInput
                      style={styles.input}
                      placeholder="Domínio (opcional)"
                      value={ldapDomain}
                      onChangeText={setLdapDomain}
                      autoCapitalize="characters"
                    />
                    <TextInput
                      style={styles.input}
                      placeholder="Senha"
                      value={ldapPassword}
                      onChangeText={setLdapPassword}
                      secureTextEntry
                    />
                    <TouchableOpacity
                      style={[styles.button, styles.ldapButton]}
                      onPress={handleLdapLogin}
                      disabled={isLoading}
                    >
                      {isLoading ? (
                        <ActivityIndicator color="#fff" />
                      ) : (
                        <Text style={styles.buttonText}>Entrar com AD/LDAP</Text>
                      )}
                    </TouchableOpacity>
                  </View>
                )}

                <View style={styles.divider}>
                  <View style={styles.dividerLine} />
                  <Text style={styles.dividerText}>ou</Text>
                  <View style={styles.dividerLine} />
                </View>
              </View>
            )}

            {/* Form de Login */}
            <View style={styles.inputContainer}>
              <Ionicons name="mail-outline" size={20} color="#9ca3af" style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                placeholder="E-mail"
                value={email}
                onChangeText={setEmail}
                keyboardType="email-address"
                autoCapitalize="none"
                autoComplete="email"
              />
            </View>

            <View style={styles.inputContainer}>
              <Ionicons name="lock-closed-outline" size={20} color="#9ca3af" style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                placeholder="Senha"
                value={password}
                onChangeText={setPassword}
                secureTextEntry={!showPassword}
                autoComplete="password"
              />
              <TouchableOpacity
                onPress={() => setShowPassword(!showPassword)}
                style={styles.eyeIcon}
              >
                <Ionicons
                  name={showPassword ? 'eye-off-outline' : 'eye-outline'}
                  size={20}
                  color="#9ca3af"
                />
              </TouchableOpacity>
            </View>

            <TouchableOpacity style={styles.forgotPassword}>
              <Text style={styles.forgotPasswordText}>Esqueci minha senha</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.button}
              onPress={handleLogin}
              disabled={isLoading}
            >
              {isLoading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.buttonText}>Entrar</Text>
              )}
            </TouchableOpacity>
          </View>

          {/* Footer */}
          <Text style={styles.footer}>
            2024 Conecta Plus. Todos os direitos reservados.
          </Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  keyboardView: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
    padding: 24,
  },
  logoContainer: {
    alignItems: 'center',
    marginBottom: 32,
  },
  logoIcon: {
    width: 80,
    height: 80,
    borderRadius: 20,
    backgroundColor: '#fff',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 8,
  },
  logoText: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
  },
  tagline: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.8)',
    marginTop: 4,
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 24,
    padding: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.15,
    shadowRadius: 16,
    elevation: 12,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#1f2937',
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 14,
    color: '#6b7280',
    textAlign: 'center',
    marginBottom: 24,
  },
  errorContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fef2f2',
    padding: 12,
    borderRadius: 12,
    marginBottom: 16,
  },
  errorText: {
    color: '#ef4444',
    marginLeft: 8,
    flex: 1,
  },
  ssoContainer: {
    marginBottom: 16,
  },
  ssoButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#e5e7eb',
    marginBottom: 8,
  },
  ssoButtonText: {
    marginLeft: 8,
    fontSize: 14,
    fontWeight: '500',
    color: '#374151',
  },
  ldapForm: {
    marginTop: 12,
    padding: 12,
    backgroundColor: '#f9fafb',
    borderRadius: 12,
  },
  ldapButton: {
    backgroundColor: '#6b7280',
    marginTop: 8,
  },
  divider: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 16,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: '#e5e7eb',
  },
  dividerText: {
    marginHorizontal: 12,
    color: '#9ca3af',
    fontSize: 12,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f9fafb',
    borderRadius: 12,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  inputIcon: {
    marginLeft: 12,
  },
  input: {
    flex: 1,
    padding: 14,
    fontSize: 16,
    color: '#1f2937',
  },
  eyeIcon: {
    padding: 12,
  },
  forgotPassword: {
    alignSelf: 'flex-end',
    marginBottom: 24,
  },
  forgotPasswordText: {
    color: '#2563eb',
    fontSize: 14,
  },
  button: {
    backgroundColor: '#2563eb',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  footer: {
    textAlign: 'center',
    color: 'rgba(255,255,255,0.6)',
    fontSize: 12,
    marginTop: 24,
  },
});
