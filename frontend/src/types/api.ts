/**
 * API 通用类型定义
 */

export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data?: T
  meta?: {
    page: number
    per_page: number
    total: number
  }
}

export interface UserInfo {
  id: number
  username: string
  real_name: string
  roles: string[]
  permissions: string[]
  must_change_password?: boolean
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: UserInfo
}

export interface RefreshResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface ScoreEntry {
  student_id: number
  subject_id: number
  total_score: number
}

export interface ClassScoreInfo {
  student_id: number
  student_name: string
  student_no: string
  subjects: Record<string, number>
  yws: Record<string, number>
  top3: Record<string, number>
  total: number
  yws_total: number
  top3_total: number
  class_rank: number | null
  grade_rank: number | null
  yws_rank?: number
  top3_rank?: number
}

export interface RankRow {
  rank: number
  class_rank: number
  student_id: number
  student_name: string
  student_no: string
  class_name: string
  total_score: number
  subject_name?: string
  yuwai_rank?: number
  yuwai_total?: number
  top3_rank?: number
  top3_total?: number
  subjects?: Record<string, number>
}

export interface ClassCompareRow {
  class_id: number
  class_name: string
  avg_score: number
  max_score: number
  min_score: number
  excellent_rate: number
  pass_rate: number
  student_count: number
}

export interface ExamInfo {
  id: number
  name: string
  exam_type: string
  semester_id: number
  grade_id: number
  enrollment_year: number
  exam_date: string | null
  status: string
  created_by: number
  created_at: string
}

export interface HealthInfo {
  status: string
  version: string
  database: string
  debug: boolean
}