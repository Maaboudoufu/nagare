/* The right-hand pane: picks the workspace for the lesson's type. */
import CodeWorkspace from './CodeWorkspace.jsx';
import Quiz from './Quiz.jsx';
import Sandbox from './Sandbox.jsx';
import StepsWorkspace from './StepsWorkspace.jsx';
import TextAnswer from './TextAnswer.jsx';

export default function Workspace({lesson, courseSlug}) {
  if (lesson.files) return <CodeWorkspace lesson={lesson}/>;
  if (lesson.questions) return <Quiz lesson={lesson}/>;
  if (lesson.sandbox) return <Sandbox lesson={lesson}/>;
  if (lesson.steps) return <StepsWorkspace lesson={lesson} courseSlug={courseSlug}/>;
  return <TextAnswer lesson={lesson}/>;
}
