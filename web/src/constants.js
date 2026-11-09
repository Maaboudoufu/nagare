export const MODES = {go:'go', py:'python', sql:'text/x-sqlite', js:'javascript', ts:'text/typescript', c:'text/x-csrc'};
export const FENCE_MODES = {go:'go', py:'python', python:'python', sql:'text/x-sqlite', sh:'shell', bash:'shell', shell:'shell',
                            yaml:'yaml', yml:'yaml', json:'application/json', jsonc:'application/json', js:'javascript', javascript:'javascript',
                            ts:'text/typescript', typescript:'text/typescript', c:'text/x-csrc', h:'text/x-csrc'};
export const TYPES = {
  type_code:['code-xml', 'Code'], type_code_tests:['code-xml', 'Code'], type_code_sql:['database', 'SQL'],
  type_choice:['list-checks', 'Quiz'], type_cli:['terminal', 'CLI'], type_shell:['terminal', 'Shell'],
  type_github_checks:['git-branch', 'GitHub'], type_interview_chat:['message-square', 'Interview'], type_text_input:['pen-line', 'Answer'],
};
export const CALLOUTS = {info:['info', 'Info', 'info'], note:['info', 'Note', 'note'], tip:['lightbulb', 'Tip', 'tip'],
                         warning:['triangle-alert', 'Warning', 'warning'], danger:['triangle-alert', 'Danger', 'danger'],
                         windows:['terminal', 'Windows', 'os'], linux:['terminal', 'Linux', 'os'], macos:['terminal', 'macOS', 'os'],
                         mobile:['info', 'Mobile', 'os'], desktop:['info', 'Desktop', 'os']};
// Course logos: [sprite symbol, tile color, name, from the Lucide sprite, full-color logo file].
// Simple Icons (one color) for most brands; AWS and Power BI aren't in Simple Icons, so their official logos are files.
export const BRANDS = {
  python:['python', '#3776AB', 'Python'], go:['go', '#00ADD8', 'Go'], typescript:['typescript', '#3178C6', 'TypeScript'],
  javascript:['javascript', '#F7DF1E', 'JavaScript'], c:['c', '#A8B9CC', 'C'], git:['git', '#F03C2E', 'Git'],
  shell:['gnubash', '#4EAA25', 'Shell'], sql:['sqlite', '#003B57', 'SQL'], docker:['docker', '#2496ED', 'Docker'],
  kubernetes:['kubernetes', '#326CE5', 'Kubernetes'], pandas:['pandas', '#150458', 'pandas'],
  rabbitmq:['rabbitmq', '#FF6600', 'RabbitMQ'], githubactions:['githubactions', '#2088FF', 'GitHub Actions'],
  aws:[null, '#232F3E', 'AWS', false, '/vendor/logos/aws.svg'], powerbi:[null, '#2B2B30', 'Power BI', false, '/vendor/logos/powerbi.svg'],
  any:['rocket', '#3A3A40', 'Project', true],
};
export const SHORT_NAMES = {'backend-python-golang':'Backend (Go)', 'backend-python-typescript':'Backend (TypeScript)',
                            'devops-python-golang':'DevOps', 'data-analyst-python':'Data Analyst'};
export const STEP_TITLES = {type_cli:['terminal', 'Run these in your terminal'], type_shell:['terminal', 'Do this in your terminal'],
                            type_github_checks:['git-branch', 'Checks run against your GitHub repo']};

// A course's logo: its main technology when that isn't the language (RabbitMQ in Go is still RabbitMQ).
const SUBJECTS = [['pandas', 'pandas'], ['rabbitmq', 'rabbitmq'], ['ci-cd', 'githubactions'], ['s3-cloudfront', 'aws']];
export const brandOf = course => BRANDS[SUBJECTS.find(([k]) => course.slug.includes(k))?.[1] ?? course.language] || BRANDS.any;
