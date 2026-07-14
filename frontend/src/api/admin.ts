import type { components } from "../types/api";
import { apiClient } from "./client";

export type Telemetry = components["schemas"]["Telemetry"];
export type UsageStats = components["schemas"]["UsageStats"];
export type WorkerTelemetry = components["schemas"]["WorkerTelemetry"];

export async function getTelemetry(): Promise<Telemetry> {
  const { data, error } = await apiClient.GET("/admin/telemetry");
  if (error) throw new Error(`getTelemetry failed: ${JSON.stringify(error)}`);
  return data;
}

export async function getUsageStats(): Promise<UsageStats> {
  const { data, error } = await apiClient.GET("/admin/stats");
  if (error) throw new Error(`getUsageStats failed: ${JSON.stringify(error)}`);
  return data;
}

export async function setWorkerCapacity(workerName: string, maximum: number): Promise<void> {
  const { error } = await apiClient.PATCH("/admin/workers/{worker_name}/capacity", {
    params: { path: { worker_name: workerName } },
    body: { max_concurrency: maximum },
  });
  if (error) throw new Error(`setWorkerCapacity failed: ${JSON.stringify(error)}`);
}
