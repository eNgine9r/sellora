import { useQuery } from "@tanstack/react-query";
import { ScrollView, Text, View } from "react-native";

import { apiRequest } from "@/services/api";

type Health = { status: string; runtime_commit?: string };

export default function HomeScreen() {
  const health = useQuery({ queryKey: ["health"], queryFn: () => apiRequest<Health>("/health", { workspaceOptional: true }) });
  return (
    <ScrollView contentInsetAdjustmentBehavior="automatic" contentContainerStyle={{ padding: 20, gap: 16 }}>
      <Text selectable style={{ fontSize: 30, fontWeight: "700" }}>Sellora Mobile PoC</Text>
      <View style={{ padding: 18, gap: 8, borderRadius: 18, borderCurve: "continuous", backgroundColor: "#171329" }}>
        <Text selectable style={{ color: "white", fontSize: 18, fontWeight: "600" }}>FastAPI compatibility probe</Text>
        <Text selectable style={{ color: "#c7c1df" }}>
          {health.isPending ? "Перевіряємо API…" : health.isError ? "API недоступний" : `Статус: ${health.data.status}`}
        </Text>
      </View>
    </ScrollView>
  );
}
