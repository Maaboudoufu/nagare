import {N_} from './lib/i18n.js';

export const MODES = {go:'go', py:'python', sql:'text/x-sqlite', js:'javascript', ts:'text/typescript', c:'text/x-csrc'};
export const FENCE_MODES = {go:'go', py:'python', python:'python', sql:'text/x-sqlite', sh:'shell', bash:'shell', shell:'shell',
                            yaml:'yaml', yml:'yaml', json:'application/json', jsonc:'application/json', js:'javascript', javascript:'javascript',
                            ts:'text/typescript', typescript:'text/typescript', c:'text/x-csrc', h:'text/x-csrc'};
export const TYPES = {
  type_code:['code-xml', N_('Code')], type_code_tests:['code-xml', N_('Code')], type_code_sql:['database', 'SQL'],
  type_choice:['list-checks', N_('Quiz')], type_cli:['terminal', 'CLI'], type_shell:['terminal', N_('Shell')],
  type_github_checks:['git-branch', 'GitHub'], type_interview_chat:['message-square', N_('Interview')], type_text_input:['pen-line', N_('Answer')],
};
export const CALLOUTS = {info:['info', N_('Info'), 'info'], note:['info', N_('Note'), 'note'], tip:['lightbulb', N_('Tip'), 'tip'],
                         warning:['triangle-alert', N_('Warning'), 'warning'], danger:['triangle-alert', N_('Danger'), 'danger'],
                         windows:['terminal', 'Windows', 'os'], linux:['terminal', 'Linux', 'os'], macos:['terminal', 'macOS', 'os'],
                         mobile:['info', N_('Mobile'), 'os'], desktop:['info', N_('Desktop'), 'os']};
// Course logos: [sprite symbol, tile color, name, from the Lucide sprite, full-color logo file].
// Simple Icons (one color) for most brands; AWS and Power BI aren't in Simple Icons, so their official logos are files.
export const BRANDS = {
  python:['python', '#3776AB', 'Python'], go:['go', '#00ADD8', 'Go'], typescript:['typescript', '#3178C6', 'TypeScript'],
  javascript:['javascript', '#F7DF1E', 'JavaScript'], c:['c', '#A8B9CC', 'C'], git:['git', '#F03C2E', 'Git'],
  shell:['gnubash', '#4EAA25', 'Shell'], sql:['sqlite', '#003B57', 'SQL'], docker:['docker', '#2496ED', 'Docker'],
  kubernetes:['kubernetes', '#326CE5', 'Kubernetes'], pandas:['pandas', '#150458', 'pandas'],
  rabbitmq:['rabbitmq', '#FF6600', 'RabbitMQ'], githubactions:['githubactions', '#2088FF', 'GitHub Actions'],
  aws:[null, '#232F3E', 'AWS', false, '/vendor/logos/aws.svg'], powerbi:[null, '#2B2B30', 'Power BI', false, '/vendor/logos/powerbi.svg'],
  any:['rocket', '#3A3A40', N_('Project'), true],
};
export const SHORT_NAMES = {'backend-python-golang':N_('Backend (Go)'), 'backend-python-typescript':N_('Backend (TypeScript)'),
                            'devops-python-golang':N_('DevOps'), 'data-analyst-python':N_('Data Analyst')};
export const STEP_TITLES = {type_cli:['terminal', N_('Run these in your terminal')], type_shell:['terminal', N_('Do this in your terminal')],
                            type_github_checks:['git-branch', N_('Checks run against your GitHub repo')]};

// A course's logo: its main technology when that isn't the language (RabbitMQ in Go is still RabbitMQ).
const SUBJECTS = [['pandas', 'pandas'], ['rabbitmq', 'rabbitmq'], ['ci-cd', 'githubactions'], ['s3-cloudfront', 'aws']];
export const brandOf = course => BRANDS[SUBJECTS.find(([k]) => course.slug.includes(k))?.[1] ?? course.language] || BRANDS.any;
