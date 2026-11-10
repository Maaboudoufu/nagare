import aws from './assets/logos/aws.svg';
import c from './assets/logos/c.svg';
import powerbi from './assets/logos/powerbi.svg';
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
// Course logos, shown on a tile of the brand's color. icon: a symbol in assets/brands.svg (Simple Icons, one color).
// img: a full-color logo file, for the brands Simple Icons doesn't have. lucide: the icon is from the UI's own set.
export const BRANDS = {
  python:{name:'Python', color:'#3776AB', icon:'python'},
  go:{name:'Go', color:'#00ADD8', icon:'go'},
  typescript:{name:'TypeScript', color:'#3178C6', icon:'typescript'},
  javascript:{name:'JavaScript', color:'#F7DF1E', icon:'javascript'},
  c:{name:'C', color:'#1E2B3C', img:c},
  git:{name:'Git', color:'#F03C2E', icon:'git'},
  shell:{name:'Shell', color:'#4EAA25', icon:'gnubash'},
  sql:{name:'SQL', color:'#003B57', icon:'sqlite'},
  docker:{name:'Docker', color:'#2496ED', icon:'docker'},
  kubernetes:{name:'Kubernetes', color:'#326CE5', icon:'kubernetes'},
  pandas:{name:'pandas', color:'#150458', icon:'pandas'},
  rabbitmq:{name:'RabbitMQ', color:'#FF6600', icon:'rabbitmq'},
  githubactions:{name:'GitHub Actions', color:'#2088FF', icon:'githubactions'},
  aws:{name:'AWS', color:'#232F3E', img:aws},
  powerbi:{name:'Power BI', color:'#2B2B30', img:powerbi},
  any:{name:N_('Project'), color:'#3A3A40', icon:'rocket', lucide:true},
};
export const SHORT_NAMES = {'backend-python-golang':N_('Backend (Go)'), 'backend-python-typescript':N_('Backend (TypeScript)'),
                            'devops-python-golang':N_('DevOps'), 'data-analyst-python':N_('Data Analyst')};
export const STEP_TITLES = {type_cli:['terminal', N_('Run these in your terminal')], type_shell:['terminal', N_('Do this in your terminal')],
                            type_github_checks:['git-branch', N_('Checks run against your GitHub repo')]};

// A course's logo: its main technology when that isn't the language (RabbitMQ in Go is still RabbitMQ).
const SUBJECTS = [['pandas', 'pandas'], ['rabbitmq', 'rabbitmq'], ['ci-cd', 'githubactions'], ['s3-cloudfront', 'aws']];
export const brandOf = course => BRANDS[SUBJECTS.find(([k]) => course.slug.includes(k))?.[1] ?? course.language] || BRANDS.any;
