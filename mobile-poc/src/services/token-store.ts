import * as SecureStore from "expo-secure-store";

const ACCESS_TOKEN = "sellora.access-token";
const REFRESH_TOKEN = "sellora.refresh-token";
const WORKSPACE_ID = "sellora.workspace-id";

export const tokenStore = {
  getAccessToken: () => SecureStore.getItemAsync(ACCESS_TOKEN),
  getRefreshToken: () => SecureStore.getItemAsync(REFRESH_TOKEN),
  getWorkspaceId: () => SecureStore.getItemAsync(WORKSPACE_ID),
  setTokens: async (accessToken: string, refreshToken: string) => {
    await Promise.all([SecureStore.setItemAsync(ACCESS_TOKEN, accessToken), SecureStore.setItemAsync(REFRESH_TOKEN, refreshToken)]);
  },
  switchWorkspace: (workspaceId: string) => SecureStore.setItemAsync(WORKSPACE_ID, workspaceId),
  clear: async () => {
    await Promise.all([SecureStore.deleteItemAsync(ACCESS_TOKEN), SecureStore.deleteItemAsync(REFRESH_TOKEN), SecureStore.deleteItemAsync(WORKSPACE_ID)]);
  },
};
