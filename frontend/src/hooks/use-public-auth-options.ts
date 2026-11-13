import { useQuery } from "@tanstack/react-query";
import { fetchPublicAuthOptions } from "@/services/auth.service";

export function usePublicAuthOptions() {
  return useQuery({ queryKey: ["public-auth-options"], queryFn: fetchPublicAuthOptions, staleTime: 60_000, retry: false });
}
