export type WorkspaceMemoKind = "NOTE" | "TASK";
export type WorkspaceMemo = {
  id: string;
  workspace_id: string;
  kind: WorkspaceMemoKind;
  title: string;
  body: string;
  due_on: string | null;
  is_pinned: boolean;
  is_done: boolean;
  created_by: string | null;
  updated_by: string | null;
  created_at: string;
  updated_at: string;
};
export type WorkspaceMemoCreate = {
  kind: WorkspaceMemoKind;
  title: string;
  body: string;
  due_on: string | null;
  is_pinned: boolean;
};
export type WorkspaceMemoUpdate = Partial<Pick<WorkspaceMemo, "title" | "body" | "due_on" | "is_pinned" | "is_done">>;
