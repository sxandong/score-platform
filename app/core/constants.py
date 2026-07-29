"""应用常量定义 - 消除魔法字符串/数字"""

# 语数外科目名称
YWYS_NAMES: set[str] = {"语文", "数学", "外语"}

# 语数外科目 ID
YWYS_IDS: tuple[int, ...] = (1, 2, 3)

# 7选3科目 ID
SEVEN_SUBJECT_IDS: tuple[int, ...] = (4, 5, 6, 7, 8, 9, 10)

# 7选3科目名称 (对应ID)
SEVEN_SUBJECT_NAMES: set[str] = {"物理", "化学", "生物", "政治", "历史", "地理", "技术"}

# 所有科目名称
ALL_SUBJECT_NAMES: list[str] = [
    "语文", "数学", "外语", "物理", "化学",
    "生物", "政治", "历史", "地理", "技术",
]

# 排名类型
RANK_TYPE_TOTAL = "total"
RANK_TYPE_SUBJECT = "subject"
RANK_TYPE_YUWAI = "yuwai"
RANK_TYPE_TOP3 = "top3"

# 用户角色
ROLE_ADMIN = "admin"
ROLE_DIRECTOR = "director"
ROLE_TEACHER = "teacher"
ROLE_STUDENT = "student"
ROLE_PARENT = "parent"

# 考试状态
EXAM_DRAFT = "draft"
EXAM_PUBLISHED = "published"
EXAM_LOCKED = "locked"

# 成绩状态
SCORE_PENDING = "pending"
SCORE_APPROVED = "approved"

# 默认科目满分
DEFAULT_FULL_SCORE = 100.0

# 优秀/及格阈值 (相对于满分)
EXCELLENT_RATIO = 0.85
PASS_RATIO = 0.60