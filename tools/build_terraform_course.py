"""The Learn Terraform course, as source: writes courses/learn-terraform.json and its entry in courses/index.json.
Edit the lessons here, not in the JSON.

Usage (from the project root):
  python3 tools/build_terraform_course.py              write the course, then run  python3 tools/fetch_media.py --images-only
                                                       (it downloads the lesson images and points the lessons at /media/...)
  python3 tools/build_terraform_course.py test <dir>   also play every hands-on lesson's solution in <dir> (a new, empty
                                                       folder used as HOME) and run the lesson's checks with server/grader.py.
                                                       Needs `tofu` on PATH and the hashicorp/local and hashicorp/random providers."""
import json, os, subprocess, sys, textwrap, uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SLUG = 'learn-terraform'
IMG = {
    'tofu': 'https://raw.githubusercontent.com/opentofu/brand-artifacts/main/full/transparent/SVG/on-dark.svg',
    'apis': 'https://web-unified-docs-hashicorp.vercel.app/api/assets/terraform/latest/img/docs/intro-terraform-apis.png',
    'flow': 'https://web-unified-docs-hashicorp.vercel.app/api/assets/terraform/latest/img/docs/intro-terraform-workflow.png',
    'graph': 'https://raw.githubusercontent.com/opentofu/opentofu/v1.13.9/website/docs/images/graph-example.png',
}
D = lambda s: textwrap.dedent(s).strip('\n') + '\n'
T = lambda folder: f'tofu -chdir=$HOME/tofu/{folder}'
CHAPTERS = []


def chapter(title):
    CHAPTERS.append({'title': title, 'lessons': []})


def _add(title, kind, readme, **more):
    lesson = {'uuid': str(uuid.uuid5(uuid.NAMESPACE_URL, f'nagare/{SLUG}/{title}')), 'title': title, 'type': kind,
              'readme': f'# {title}\n\n' + D(readme), **more}
    CHAPTERS[-1]['lessons'].append(lesson)


def quiz(title, readme, *questions):
    """questions: (question, right answer, wrong answers...). at: where the right answer goes in the list."""
    qs = []
    for n, (q, right, *wrong) in enumerate(questions):
        answers = list(wrong)
        answers.insert((len(title) + n) % (len(wrong) + 1), right)
        qs.append({'question': q, 'answers': answers, 'answer': right})
    _add(title, 'type_choice', readme, questions=qs)


def check(description, command, contains=(), none=(), jq=None, exit=0):
    """One check. jq: (query, expected value)."""
    tests, expects = [], []
    blank = {'exitCode': None, 'stdoutContainsAll': None, 'stdoutContainsNone': None, 'stdoutLinesGT': None, 'stdoutJq': None}
    if exit is not None:
        tests.append({**blank, 'exitCode': exit}); expects.append(f'exit code {exit}')
    if contains:
        tests.append({**blank, 'stdoutContainsAll': list(contains)})
        expects.append('output contains: ' + ', '.join(f"'{c}'" for c in contains))
    if none:
        tests.append({**blank, 'stdoutContainsNone': list(none)})
        expects.append("output doesn't contain: " + ', '.join(f"'{c}'" for c in none))
    if jq:
        q = {'inputMode': '', 'query': jq[0], 'expectedResults': [{'type': type(jq[1]).__name__.replace('str', 'string'), 'operator': '==', 'value': jq[1]}]}
        tests.append({**blank, 'stdoutJq': q}); expects.append('jq check: ' + json.dumps(q))
    return ({'description': description, 'command': command, 'expects': expects},
            {'description': description, 'cliCommand': {'command': command, 'tests': tests, 'stdoutVariables': None, 'sleepAfterMs': None,
                                                         'stdoutFilterTmdl': None}, 'httpRequest': None, 'noPenaltyOnFail': True})


SOLUTIONS = {}  # lesson title -> (shell script that does the assignment, whether the checks should fail before it)


def cli(title, readme, checks, solution='', fails_before=True):
    _add(title, 'type_cli', readme, steps=[c[0] for c in checks], cli=[c[1] for c in checks], baseURL=None)
    SOLUTIONS[title] = (D(solution).replace('TFLOCAL\n', TF_LOCAL + '\n'), fails_before)


TF_LOCAL = '''terraform {
  required_providers {
    local = {
      source = "hashicorp/local"
    }
  }
}
'''

# ------------------------------------------------------------------------------------------------ Introduction
chapter('Introduction')

cli('Welcome to Learn Terraform', f'''
    ![OpenTofu logo]({IMG['tofu']})

    Clicking around a cloud console works until you have to do it twice. In this course you'll describe infrastructure in text files and let a tool build it for you, the same way, every time.

    ## Learning Goals

    - Understand what infrastructure as code is and why teams use it.
    - Write configuration: providers, resources, variables, outputs, and modules.
    - Run the core workflow with confidence: `init`, `plan`, `apply`, `destroy`.
    - Understand state, the thing that trips up most beginners.

    ## Terraform or OpenTofu?

    [Terraform](https://developer.hashicorp.com/terraform) is the tool that made infrastructure as code mainstream. [OpenTofu](https://opentofu.org/) is its open-source fork. They share the same language, the same workflow, and almost all of the same commands.

    **This course uses OpenTofu.** It's free, open source, and already installed in your workspace. Everything you learn here applies to Terraform too: wherever you see `tofu`, a Terraform user types `terraform`.

    ```bash
    tofu plan       # OpenTofu
    terraform plan  # Terraform, same thing
    ```

    The next lesson covers the differences.

    ## Your Workspace

    - The terminal on the right is yours. Files you create are kept between visits.
    - Each chapter gets its own folder inside `~/tofu`, so one chapter's mistakes never break the next.
    - Edit files with `nano` or `vim`.
    - **Run checks** tests your work and marks the lesson complete when it passes.

    > [!info]
    > You won't need a cloud account. The lessons manage local files and random values, which is free, instant, and teaches the exact same workflow you'd use on AWS.

    ## Assignment

    1. [ ] Check that OpenTofu is installed:
       ```bash
       tofu version
       ```

    **Run** the checks.
    ''', [check('Check OpenTofu is installed', 'tofu version', contains=['OpenTofu'])], fails_before=False)

quiz('Terraform vs. OpenTofu', '''
    Same language, same workflow, different owners.

    ## A Short History

    - **2014:** HashiCorp releases Terraform as open source ([MPL 2.0](https://www.mozilla.org/en-US/MPL/2.0/)).
    - **August 2023:** HashiCorp moves Terraform to the [Business Source License](https://www.hashicorp.com/bsl). You can still use it for free, but you can't build a product that competes with HashiCorp on top of it.
    - **September 2023:** The community forks the last open-source version. The fork joins the Linux Foundation as **OpenTofu**.
    - **January 2024:** OpenTofu 1.6, the first stable release.
    - **2025:** IBM completes its acquisition of HashiCorp.

    ## What's the Same

    - The configuration language. Your `.tf` files work in both.
    - The workflow: `init`, `plan`, `apply`, `destroy`.
    - Providers and modules. The same ones work with both tools.
    - The state file format.

    ## What's Different

    |          | Terraform                   | OpenTofu                        |
    | -------- | --------------------------- | ------------------------------- |
    | Command  | `terraform`                 | `tofu`                          |
    | License  | BUSL 1.1 (source-available) | MPL 2.0 (open source)           |
    | Owner    | HashiCorp (IBM)             | Linux Foundation                |
    | Registry | `registry.terraform.io`     | `registry.opentofu.org`         |
    | Extras   | HCP Terraform integration   | Built-in state encryption       |

    The two have slowly drifted apart since the fork, each adding features the other lacks. The fundamentals in this course are identical in both.

    > [!tip]
    > Job postings almost always say "Terraform". The skills are the same, so say you know both.
    ''',
    ('Why does OpenTofu exist?',
     'Terraform changed to a license that is no longer open source, so the community forked it',
     'Terraform was shut down by HashiCorp',
     'Terraform only works on AWS, and OpenTofu supports every cloud',
     'OpenTofu uses a completely different, simpler language'),
    ('A teammate wrote `main.tf` for Terraform. What do you most likely need to change to use it with OpenTofu?',
     'Nothing in the file. Run `tofu` instead of `terraform`',
     'Rewrite every resource block in OpenTofu syntax',
     'Rename the file to `main.tofu.yaml`',
     'Convert the state file by hand'))

quiz('Infrastructure as Code', '''
    Infrastructure is everything your app runs on: servers, databases, networks, DNS records, storage buckets.

    You can create it by hand, clicking through a web console. That's fine once. Then:

    - You need the same setup for staging. Which boxes did you tick?
    - Something broke. Who changed what, and when?
    - A teammate needs to review a change _before_ it happens.

    **Infrastructure as code** (IaC) fixes this. You describe your infrastructure in text files, and a tool makes reality match.

    ```hcl
    resource "aws_instance" "web" {
      ami           = "ami-0abc1234"
      instance_type = "t3.micro"
    }
    ```

    Because it's just text, you get everything you already get with code:

    - **Version control:** every change is in Git.
    - **Review:** changes go through pull requests.
    - **Repeatable:** the same files build the same infrastructure, every time.
    - **Automation:** a CI pipeline can roll out changes for you.
    ''',
    ('Which problem does infrastructure as code solve best?',
     'Recreating the same infrastructure reliably, with a history of every change',
     'Making servers run faster',
     'Removing the need for cloud providers',
     'Writing application code automatically'))

quiz('How Terraform Works', f'''
    Terraform doesn't know how to create a server. It knows how to _ask_.

    Every platform has an API: AWS, Cloudflare, GitHub, Kubernetes. Terraform talks to those APIs through plugins called **providers**. There are thousands of them.

    ![Terraform uses providers to talk to each platform's API]({IMG['apis']})

    -- Source: [HashiCorp, "What is Terraform?"](https://developer.hashicorp.com/terraform/intro)

    So there are two parts:

    - **Core:** the `tofu` (or `terraform`) program. It reads your files, works out what needs to change, and in what order.
    - **Providers:** plugins that know one platform each. Core tells the AWS provider "create this server", and the provider makes the API calls.

    ## Declarative

    You describe _what you want_, not the steps to get there.

    - **Imperative (a script):** "Create a server. Then create a database. Then connect them."
    - **Declarative (Terraform):** "There should be one server and one database, connected."

    Terraform compares what you asked for with what exists, and does only what's needed to close the gap.
    ''',
    ("What is a provider?",
     "A plugin that lets Terraform manage one platform through that platform's API",
     'A company that hosts your servers',
     'The file where Terraform saves what it created',
     'A person who approves infrastructure changes'),
    ('Your files describe 3 servers. 2 already exist. What does Terraform do?',
     'Creates 1 server',
     'Creates 3 more servers',
     'Deletes the 2 servers, then creates 3',
     'Fails, because servers already exist'))

# ------------------------------------------------------------------------------------------------ Core workflow
chapter('The Core Workflow')

quiz('Write, Plan, Apply', f'''
    Almost everything you do with Terraform is this loop:

    1. **Write:** describe what you want in `.tf` files.
    2. **Plan:** preview what would change. Nothing is touched yet.
    3. **Apply:** make the changes.

    ![The Terraform workflow: write, plan, apply]({IMG['flow']})

    -- Source: [HashiCorp, "What is Terraform?"](https://developer.hashicorp.com/terraform/intro)

    ## The Commands

    | Command        | What it does                                        |
    | -------------- | --------------------------------------------------- |
    | `tofu init`    | Sets up the folder and downloads providers. Run it first. |
    | `tofu plan`    | Shows what would change. Changes nothing.           |
    | `tofu apply`   | Shows the plan, asks for a "yes", then makes the changes. |
    | `tofu destroy` | Removes everything this folder manages.             |

    > [!tip]
    > Read the plan. Every time. It's the cheapest way to catch an expensive mistake.
    ''',
    ('Which command is safe to run at any time, because it changes nothing?',
     '`tofu plan`',
     '`tofu apply`',
     '`tofu destroy`',
     '`tofu apply -auto-approve`'))

cli('Init', '''
    Time to write some configuration. A Terraform project is just a folder of `.tf` files.

    ## Your First Resource

    A **resource** is one thing Terraform manages. In real life that's a server or a database. Here it's a file on disk, because that's free and instant:

    ```hcl
    resource "local_file" "hello" {
      filename = "hello.txt"
      content  = "Hello, Tofu!\\n"
    }
    ```

    Read it as: "there should be a `local_file`, which I'll call `hello`, with this name and this content."

    ## Init

    The `local_file` resource comes from the `local` provider. `tofu init` reads your files, sees which providers you need, and installs them into a hidden `.terraform` folder.

    Run `init` once per project, and again whenever you add a provider or module.

    ## Assignment

    1. [ ] Create a folder for this chapter and move into it:
       ```bash
       mkdir -p ~/tofu/hello && cd ~/tofu/hello
       ```
    2. [ ] Create `main.tf` with this content:
       ```hcl
       terraform {
         required_providers {
           local = {
             source = "hashicorp/local"
           }
         }
       }

       resource "local_file" "hello" {
         filename = "hello.txt"
         content  = "Hello, Tofu!\\n"
       }
       ```
    3. [ ] Initialize the project:
       ```bash
       tofu init
       ```

    **Run** the checks.
    ''', [check('Check the project is initialized', T('hello') + ' validate', contains=['Success!']),
          check('Check the local provider is required', T('hello') + ' providers', contains=['hashicorp/local'])],
    '''
    mkdir -p ~/tofu/hello && cd ~/tofu/hello
    cat > main.tf <<'EOF'
    TFLOCAL
    resource "local_file" "hello" {
      filename = "hello.txt"
      content  = "Hello, Tofu!\\n"
    }
    EOF
    tofu init
    ''')

cli('Plan', '''
    `tofu plan` compares your files with what exists and prints what it _would_ do.

    ```
      # local_file.hello will be created
      + resource "local_file" "hello" {
          + content  = "Hello, Tofu!\\n"
          + filename = "hello.txt"
          + id       = (known after apply)
        }

    Plan: 1 to add, 0 to change, 0 to destroy.
    ```

    ## Reading a Plan

    | Symbol | Meaning                          |
    | ------ | -------------------------------- |
    | `+`    | Create                           |
    | `-`    | Destroy                          |
    | `~`    | Change in place                  |
    | `-/+`  | Destroy, then create a new one   |

    `(known after apply)` means the value doesn't exist until the resource does, like a server's IP address.

    The last line is the summary. If you expected "1 to add" and it says "12 to destroy", stop.

    ## Assignment

    1. [ ] In `~/tofu/hello`, preview the changes:
       ```bash
       tofu plan
       ```
    2. [ ] Find the summary line. Nothing has been created yet: `ls` to confirm there's no `hello.txt`.

    **Run** the checks.
    ''', [check('Check the plan creates one resource', T('hello') + ' plan -no-color',
                contains=['local_file.hello will be created', 'Plan: 1 to add, 0 to change, 0 to destroy'])],
    'cd ~/tofu/hello && tofu plan', fails_before=False)

cli('Apply', '''
    `tofu apply` runs a plan, shows it to you, and waits. Only `yes` makes it real.

    ```
    Do you want to perform these actions?
      OpenTofu will perform the actions described above.
      Only 'yes' will be accepted to approve.

      Enter a value:
    ```

    After a successful apply, two things are true:

    1. The resource exists.
    2. Terraform has written down what it created in a file called `terraform.tfstate`. That's the **state**. More on it later, but for now: it's how Terraform remembers what it manages.

    > [!warning]
    > `tofu apply -auto-approve` skips the question. Handy in automation, risky at a keyboard.

    ## Assignment

    1. [ ] Apply your configuration and answer `yes`:
       ```bash
       tofu apply
       ```
    2. [ ] Look at what was created:
       ```bash
       cat hello.txt
       ```
    3. [ ] List what Terraform now manages:
       ```bash
       tofu state list
       ```

    **Run** the checks.
    ''', [check('Check the file was created', 'cat $HOME/tofu/hello/hello.txt', contains=['Hello, Tofu!']),
          check('Check the resource is in the state', T('hello') + ' state list', contains=['local_file.hello'])],
    'cd ~/tofu/hello && tofu apply -auto-approve')

cli('Change', '''
    To change infrastructure, you don't run a "change" command. You edit the file and apply again.

    Terraform compares three things: your files, the state, and reality. Then it works out the smallest set of changes.

    ## Update or Replace?

    Some changes can be made in place (`~`). Others can't, so Terraform destroys the resource and creates a new one (`-/+`). The provider decides which.

    A file's content is one of those "can't change in place" values:

    ```
      # local_file.hello must be replaced
    -/+ resource "local_file" "hello" {
          ~ content  = "Hello, Tofu!\\n" -> "Hello again, Tofu!\\n" # forces replacement
        }

    Plan: 1 to add, 0 to change, 1 to destroy.
    ```

    For a text file, who cares. For a production database, `# forces replacement` is the most important line in the plan.

    ## Assignment

    1. [ ] In `main.tf`, change the content to `"Hello again, Tofu!\\n"`.
    2. [ ] Run `tofu plan` and find `# forces replacement`.
    3. [ ] Run `tofu apply` and answer `yes`.
    4. [ ] Run `tofu plan` once more. It should say `No changes`.

    **Run** the checks.
    ''', [check('Check the file has the new content', 'cat $HOME/tofu/hello/hello.txt', contains=['Hello again, Tofu!']),
          check('Check nothing is left to change', T('hello') + ' plan -no-color -detailed-exitcode', contains=['No changes'])],
    '''cd ~/tofu/hello && sed -i 's/Hello, Tofu!/Hello again, Tofu!/' main.tf && tofu apply -auto-approve''')

quiz('Desired State', '''
    You just ran `tofu plan` right after an apply and got:

    ```
    No changes. Your infrastructure matches the configuration.
    ```

    That's the whole idea. Your files describe the **desired state**. Applying doesn't mean "run these steps". It means "make reality match".

    So running `apply` twice doesn't create two files. The second run finds nothing to do. Tools that behave this way are called **idempotent**: doing it once and doing it ten times end the same.

    This is why Terraform is safer than a shell script full of `create` commands. Run that script twice and you get two of everything.
    ''',
    ('You apply a configuration with one server. Then you run `tofu apply` again without changing anything. What happens?',
     'Nothing. The plan shows no changes',
     'A second server is created',
     'The server is destroyed and recreated',
     'An error, because the server already exists'),
    ('You change a server\'s size in your `.tf` file, but never run `apply`. What is true?',
     'The real server is unchanged, and `tofu plan` would show the difference',
     'The real server resized itself automatically',
     'The state file is now corrupted',
     'Terraform will refuse to run until you undo the edit'))

cli('Destroy', '''
    `tofu destroy` removes every resource the project manages. It shows a plan first and asks for `yes`, just like apply.

    ```
    Plan: 0 to add, 0 to change, 1 to destroy.
    ```

    It only touches what's in this project's state. Anything Terraform didn't create is left alone.

    ## Removing One Thing

    You rarely destroy everything. To remove a single resource, delete its block from the `.tf` file and run `tofu apply`. The plan will show it being destroyed.

    > [!danger]
    > In a real project, `destroy` deletes real servers and real data. There's no undo.

    ## Assignment

    1. [ ] In `~/tofu/hello`, destroy the project and answer `yes`:
       ```bash
       tofu destroy
       ```
    2. [ ] Confirm the file is gone with `ls`, and that `tofu state list` prints nothing.

    **Run** the checks.
    ''', [check('Check the file is gone', 'test ! -e $HOME/tofu/hello/hello.txt'),
          check('Check the state is empty', T('hello') + ' state list', none=['local_file.hello'])],
    'cd ~/tofu/hello && tofu destroy -auto-approve')

# ------------------------------------------------------------------------------------------------ Language
chapter('Configuration Language')

quiz('Blocks and Arguments', '''
    Terraform files are written in **HCL** (HashiCorp Configuration Language). There's really only one shape to learn: the **block**.

    ```hcl
    resource "local_file" "hello" {
      filename = "hello.txt"
      content  = "Hello!"
    }
    ```

    - `resource` is the **block type**. Others you'll meet: `variable`, `output`, `provider`, `module`.
    - `"local_file"` and `"hello"` are **labels**. For a resource: its type, then a name you choose.
    - Inside the braces are **arguments**: `name = value`.

    The name (`hello`) is only for you, to refer to this resource elsewhere in your files. The platform never sees it.

    ## Files

    - Terraform loads **every** `.tf` file in the folder and treats them as one.
    - Order doesn't matter, within a file or across files.
    - File names are conventions: `main.tf`, `variables.tf`, `outputs.tf`.

    ```hcl
    # This is a comment
    ```
    ''',
    ('In `resource "aws_instance" "web" { ... }`, what is `web`?',
     'A name you choose, used to refer to this resource in your configuration',
     'The type of resource to create',
     'The name the server will have in AWS',
     'The provider to use'),
    ('A folder has `network.tf` and `servers.tf`. Which does Terraform read first?',
     "It doesn't matter. All `.tf` files in the folder are treated as one configuration",
     '`network.tf`, because files are read alphabetically and order matters',
     'Only `main.tf` is read, so neither',
     'Whichever was edited most recently'))

cli('Providers', '''
    A provider is a plugin that teaches Terraform about one platform. You say which ones you need in a `required_providers` block:

    ```hcl
    terraform {
      required_providers {
        random = {
          source  = "hashicorp/random"
          version = "~> 3.9"
        }
      }
    }
    ```

    - `source` is where it comes from in the registry: `namespace/name`.
    - `version` limits which versions are allowed.

    ## Version Constraints

    | Constraint | Allows                                  |
    | ---------- | --------------------------------------- |
    | `3.9.1`    | Exactly 3.9.1                           |
    | `>= 3.9`   | 3.9 or anything newer                   |
    | `~> 3.9`   | 3.9 up to, but not including, 4.0       |

    `~>` is the usual choice: you get bug fixes, but not a major version that might break you.

    ## The Lock File

    `tofu init` records the exact versions it picked in `.terraform.lock.hcl`. Commit that file to Git, and everyone on the team gets the same versions.

    > [!info]
    > Your workspace has two providers pre-installed: `hashicorp/local` and `hashicorp/random`.

    ## Assignment

    1. [ ] Create a new folder for this chapter:
       ```bash
       mkdir -p ~/tofu/pets && cd ~/tofu/pets
       ```
    2. [ ] Create `main.tf`:
       ```hcl
       terraform {
         required_providers {
           random = {
             source  = "hashicorp/random"
             version = "~> 3.9"
           }
           local = {
             source  = "hashicorp/local"
             version = "~> 2.9"
           }
         }
       }
       ```
    3. [ ] Run `tofu init`, then read the lock file:
       ```bash
       cat .terraform.lock.hcl
       ```

    **Run** the checks.
    ''', [check('Check both providers are locked', 'cat $HOME/tofu/pets/.terraform.lock.hcl', contains=['hashicorp/random', 'hashicorp/local'])],
    '''
    mkdir -p ~/tofu/pets && cd ~/tofu/pets
    cat > main.tf <<'EOF'
    terraform {
      required_providers {
        random = {
          source  = "hashicorp/random"
          version = "~> 3.9"
        }
        local = {
          source  = "hashicorp/local"
          version = "~> 2.9"
        }
      }
    }
    EOF
    tofu init
    ''')

cli('Resources', '''
    Every resource has:

    - **Arguments:** values you set.
    - **Attributes:** values you can read. Some only exist after the resource is created.

    The `random` provider makes random values. Useful for unique names, and great for practice:

    ```hcl
    resource "random_pet" "name" {
      length = 2
    }
    ```

    `length` is an argument: how many words. After apply, the resource has an `id` attribute holding the generated name, like `fluent-walrus`.

    The value is generated once and saved in the state. Applying again doesn't change it.

    ## Assignment

    1. [ ] Add the `random_pet` resource above to `~/tofu/pets/main.tf`.
    2. [ ] Apply it:
       ```bash
       tofu apply
       ```
    3. [ ] Read the resource's attributes, and find your pet's name:
       ```bash
       tofu state show random_pet.name
       ```

    **Run** the checks.
    ''', [check('Check the pet exists', T('pets') + ' state list', contains=['random_pet.name'])],
    '''
    cd ~/tofu/pets
    cat >> main.tf <<'EOF'

    resource "random_pet" "name" {
      length = 2
    }
    EOF
    tofu apply -auto-approve
    ''')

cli('References', '''
    Resources get useful when they use each other's values. A reference looks like this:

    ```
    <TYPE>.<NAME>.<ATTRIBUTE>
    ```

    So the pet's generated name is `random_pet.name.id`.

    To put a value inside a string, wrap it in `${ }`:

    ```hcl
    resource "local_file" "pet" {
      filename = "pet.txt"
      content  = "My pet is ${random_pet.name.id}\\n"
    }
    ```

    In real projects this is how things connect: a server refers to its network's ID, a DNS record refers to the server's IP address.

    ## Assignment

    1. [ ] Add the `local_file` resource above to `~/tofu/pets/main.tf`.
    2. [ ] Run `tofu apply`.
    3. [ ] Run `cat pet.txt`.

    **Run** the checks.
    ''', [check('Check the file names your pet', 'cat $HOME/tofu/pets/pet.txt', contains=['My pet is ']),
          check('Check both resources are in the state', T('pets') + ' state list', contains=['random_pet.name', 'local_file.pet'])],
    '''
    cd ~/tofu/pets
    cat >> main.tf <<'EOF'

    resource "local_file" "pet" {
      filename = "pet.txt"
      content  = "My pet is ${random_pet.name.id}\\n"
    }
    EOF
    tofu apply -auto-approve
    ''')

quiz('Dependencies', '''
    The file needs the pet's name, so the pet must be created first. You never told Terraform that. It worked it out from the reference.

    Terraform builds a **dependency graph** of everything in your configuration:

    ![A dependency graph of resources](GRAPHURL)

    -- Source: [OpenTofu docs](https://opentofu.org/docs/cli/commands/graph/)

    From the graph, it knows:

    - **What order to go in.** Dependencies first. On destroy, the reverse.
    - **What can run at the same time.** Unrelated resources are created in parallel.

    That's why the order of blocks in your files doesn't matter.

    ## Hidden Dependencies

    Sometimes one resource needs another but doesn't use any of its values. Then you say so yourself:

    ```hcl
    resource "local_file" "pet" {
      # ...
      depends_on = [random_pet.name]
    }
    ```

    Use `depends_on` only when there's no reference to do the job.

    > [!tip]
    > `tofu graph` prints the graph for your project.
    '''.replace('GRAPHURL', IMG['graph']),
    ('How did Terraform know to create `random_pet.name` before `local_file.pet`?',
     "The file's content refers to `random_pet.name.id`",
     'The pet block comes first in `main.tf`',
     'Resources are created in alphabetical order',
     'Random resources are always created first'),
    ('Two resources don\'t refer to each other at all. How does Terraform create them?',
     'In parallel, since neither depends on the other',
     'In the order they appear in the file',
     'It refuses until you add `depends_on`',
     'One per `tofu apply` run'))

cli('Format and Validate', '''
    Two commands keep your files tidy and catch mistakes early. Neither one touches your infrastructure.

    ## Format

    ```bash
    tofu fmt
    ```

    Rewrites your `.tf` files in the standard style: two-space indents, aligned `=` signs. It prints the names of files it changed. Nobody argues about style, because there's only one.

    ## Validate

    ```bash
    tofu validate
    ```

    Checks that the configuration makes sense: valid syntax, no unknown arguments, no references to things that don't exist. It doesn't contact any platform, so it's fast.

    ## Assignment

    1. [ ] Add this badly formatted resource to `~/tofu/pets/main.tf`, exactly as written:
       ```hcl
       resource "random_integer" "lucky" {
       min=1
             max    =   100
       }
       ```
    2. [ ] Run `tofu fmt`, then look at the file again.
    3. [ ] Run `tofu validate`.
    4. [ ] Run `tofu apply`.

    **Run** the checks.
    ''', [check('Check the files are formatted', f"grep -q random_integer $HOME/tofu/pets/main.tf && {T('pets')} fmt -check"),
          check('Check the configuration is valid', T('pets') + ' validate', contains=['Success!']),
          check('Check the lucky number exists', T('pets') + ' state list', contains=['random_integer.lucky'])],
    '''
    cd ~/tofu/pets
    cat >> main.tf <<'EOF'

    resource "random_integer" "lucky" {
    min=1
          max    =   100
    }
    EOF
    tofu fmt && tofu validate && tofu apply -auto-approve
    ''')

# ------------------------------------------------------------------------------------------------ Variables
chapter('Variables and Outputs')

cli('Input Variables', '''
    Hard-coded values make a configuration single-use. **Variables** turn it into something you can reuse.

    ```hcl
    variable "name" {
      type        = string
      description = "Who to greet"
      default     = "World"
    }
    ```

    Use it with `var.<NAME>`:

    ```hcl
    content = "Hello, ${var.name}!\\n"
    ```

    - `type` rejects wrong values early.
    - `description` tells your teammates what it's for.
    - `default` is used when no value is given. Without a default, Terraform asks you for one.

    One way to pass a value is the `-var` flag:

    ```bash
    tofu apply -var name=Tofu
    ```

    ## Assignment

    1. [ ] Create a new folder:
       ```bash
       mkdir -p ~/tofu/greeting && cd ~/tofu/greeting
       ```
    2. [ ] Create `main.tf`:
       ```hcl
       terraform {
         required_providers {
           local = {
             source = "hashicorp/local"
           }
         }
       }

       variable "name" {
         type        = string
         description = "Who to greet"
         default     = "World"
       }

       resource "local_file" "greeting" {
         filename = "greeting.txt"
         content  = "Hello, ${var.name}!\\n"
       }
       ```
    3. [ ] Run `tofu init`, then `tofu apply`. Check `greeting.txt`.
    4. [ ] Apply again with a different name, and check the file again:
       ```bash
       tofu apply -var name=Tofu
       ```

    **Run** the checks.
    ''', [check('Check the greeting exists', 'cat $HOME/tofu/greeting/greeting.txt', contains=['Hello, ']),
          check('Check the name comes from the variable', T('greeting') + ' plan -no-color -var name=Checker', contains=['Hello, Checker!'])],
    '''
    mkdir -p ~/tofu/greeting && cd ~/tofu/greeting
    cat > main.tf <<'EOF'
    TFLOCAL
    variable "name" {
      type        = string
      description = "Who to greet"
      default     = "World"
    }

    resource "local_file" "greeting" {
      filename = "greeting.txt"
      content  = "Hello, ${var.name}!\\n"
    }
    EOF
    tofu init && tofu apply -auto-approve && tofu apply -auto-approve -var name=Tofu
    ''')

cli('Setting Variables', '''
    Typing `-var` every time gets old. There are four ways to set a variable. When several set the same one, the one lower in this table wins:

    | Where                          | Example                          |
    | ------------------------------ | -------------------------------- |
    | `default` in the variable block | `default = "World"`              |
    | Environment variable           | `export TF_VAR_name=Tofu`        |
    | `terraform.tfvars` file        | `name = "Tofu"`                  |
    | Command line                   | `-var name=Tofu`                 |

    ## Variable Files

    A `.tfvars` file is just a list of values:

    ```hcl
    name = "Tofu"
    ```

    Terraform loads `terraform.tfvars` automatically. Other files are loaded when you ask: `tofu apply -var-file=prod.tfvars`. That's a common way to run the same configuration for different environments.

    > [!warning]
    > Never commit a `.tfvars` file that contains secrets.

    ## Assignment

    1. [ ] In `~/tofu/greeting`, create `terraform.tfvars`:
       ```hcl
       name = "Nagare"
       ```
    2. [ ] Run `tofu apply`, with no `-var` flag.
    3. [ ] Check `greeting.txt`.

    **Run** the checks.
    ''', [check('Check the name comes from terraform.tfvars', 'cat $HOME/tofu/greeting/greeting.txt', contains=['Hello, Nagare!']),
          check('Check nothing is left to change', T('greeting') + ' plan -no-color -detailed-exitcode', contains=['No changes'])],
    '''cd ~/tofu/greeting && echo 'name = "Nagare"' > terraform.tfvars && tofu apply -auto-approve''')

quiz('Types and Validation', '''
    ## Types

    | Type           | Example                              |
    | -------------- | ------------------------------------ |
    | `string`       | `"hello"`                            |
    | `number`       | `3` or `2.5`                         |
    | `bool`         | `true`                               |
    | `list(string)` | `["a", "b"]`                         |
    | `map(string)`  | `{ env = "prod", team = "web" }`     |
    | `object({...})`| `{ name = "web", port = 8080 }`      |

    Read from a list with an index, `var.zones[0]`, and from a map or object with a key, `var.tags["env"]` or `var.server.port`.

    ## Validation

    A type check isn't always enough. A `validation` block adds your own rule:

    ```hcl
    variable "port" {
      type = number

      validation {
        condition     = var.port >= 1024
        error_message = "Port must be 1024 or higher."
      }
    }
    ```

    A bad value now fails at plan time with your message, before anything is created.

    ## Sensitive Values

    ```hcl
    variable "db_password" {
      type      = string
      sensitive = true
    }
    ```

    `sensitive` hides the value in plan and apply output. It is **still saved in the state file** in plain text. More on that in the State chapter.
    ''',
    ('`variable "port" { type = number }` is given the value `"eighty"`. What happens?',
     'Terraform reports an error before creating anything',
     'The port is set to 0',
     'The value is silently converted to 80',
     'The resource is created, then fails'),
    ('What does `sensitive = true` do?',
     'Hides the value in command output, but not in the state file',
     'Encrypts the value everywhere, including the state file',
     'Stops the value from being used in resources',
     'Deletes the value after apply'))

cli('Locals', '''
    A **local** is a named value you compute once and reuse. Think of it as a constant inside your configuration.

    ```hcl
    locals {
      message = "Hello, ${var.name}!"
    }
    ```

    Use it with `local.<NAME>`. Note: the block is `locals`, the reference is `local`.

    ```hcl
    content = "${local.message}\\n"
    ```

    ## Variable or Local?

    - **Variable:** a value that comes from _outside_. The person running Terraform sets it.
    - **Local:** a value worked out _inside_. Nobody can override it.

    Use locals to stop repeating yourself, and to give a long expression a readable name.

    ## Assignment

    1. [ ] In `~/tofu/greeting/main.tf`, add the `locals` block above.
    2. [ ] Change the file's content to `"${local.message}\\n"`.
    3. [ ] Run `tofu plan`.

    The plan says `No changes`. You restructured the code, but the result is identical, and the plan proves it. That's a safe refactor.

    **Run** the checks.
    ''', [check('Check the local is used', "grep -c 'local.message' $HOME/tofu/greeting/main.tf"),
          check('Check the refactor changed nothing', T('greeting') + ' plan -no-color -detailed-exitcode', contains=['No changes'])],
    '''
    cd ~/tofu/greeting
    sed -i 's/content  = "Hello, ${var.name}!\\\\n"/content  = "${local.message}\\\\n"/' main.tf
    cat >> main.tf <<'EOF'

    locals {
      message = "Hello, ${var.name}!"
    }
    EOF
    tofu plan
    ''')

cli('Outputs', '''
    Variables go in. **Outputs** come out.

    ```hcl
    output "message" {
      value = local.message
    }
    ```

    After an apply, Terraform prints every output. This is how you get at the values you actually need: a server's IP address, a database's URL.

    ```
    Outputs:

    message = "Hello, Nagare!"
    ```

    Read them again any time, without applying:

    ```bash
    tofu output               # all of them
    tofu output message       # one, quoted
    tofu output -raw message  # one, plain text: good for scripts
    tofu output -json         # everything as JSON
    ```

    ## Assignment

    1. [ ] In `~/tofu/greeting/main.tf`, add two outputs:
       ```hcl
       output "message" {
         value = local.message
       }

       output "path" {
         value = local_file.greeting.filename
       }
       ```
    2. [ ] Run `tofu apply`.
    3. [ ] Run `tofu output -raw message`.

    **Run** the checks.
    ''', [check('Check the message output', T('greeting') + ' output -raw message', contains=['Hello, Nagare!']),
          check('Check the path output', T('greeting') + ' output -raw path', contains=['greeting.txt'])],
    '''
    cd ~/tofu/greeting
    cat >> main.tf <<'EOF'

    output "message" {
      value = local.message
    }

    output "path" {
      value = local_file.greeting.filename
    }
    EOF
    tofu apply -auto-approve
    ''')

# ------------------------------------------------------------------------------------------------ State
chapter('State')

quiz('What Is State?', '''
    How does Terraform know that `local_file.greeting` in your code is _that_ file on disk? Or that a block called `web` is server `i-0abc123` in AWS?

    It wrote it down. After every apply, Terraform saves what it created in a **state file**: `terraform.tfstate`.

    State is the link between three things:

    - **Configuration:** what you want (your `.tf` files).
    - **State:** what Terraform believes exists.
    - **Reality:** what actually exists.

    On every plan, Terraform refreshes the state from reality, then compares it with your configuration.

    ## Rules

    - **Don't edit it by hand.** It's JSON and you _can_ read it, but use `tofu state` commands to change it.
    - **Don't lose it.** Without state, Terraform has no idea what it manages. It would try to create everything again.
    - **Don't commit it to Git.** It can contain passwords and keys, in plain text.

    ## Assignment

    In `~/tofu/greeting`, run these, then answer the questions:

    ```bash
    tofu state list
    tofu state show local_file.greeting
    ```
    ''',
    ('What does `tofu state list` print in `~/tofu/greeting`?',
     '`local_file.greeting`',
     '`greeting.txt`',
     '`var.name`',
     '`main.tf`'),
    ('You delete `terraform.tfstate`, then run `tofu plan`. Your `.tf` files are unchanged. What does the plan show?',
     'Everything will be created, because Terraform no longer knows it exists',
     'No changes',
     'Everything will be destroyed',
     'An error asking you to restore the file'))

cli('Drift', '''
    Reality doesn't always stay the way Terraform left it. Someone clicks in the console. A script deletes a file. That's **drift**: the real world no longer matches the state.

    Terraform handles it without drama. Every plan starts by checking reality, so drift shows up as a difference:

    ```
      # local_file.greeting will be created
      + resource "local_file" "greeting" {
    ```

    Your configuration still says the file should exist, so the fix is to apply. Terraform puts things back.

    This cuts both ways. If a teammate fixes something by hand and doesn't update the `.tf` files, the next apply **undoes their fix**. The files are the source of truth, so every change should go through them.

    ## Assignment

    1. [ ] In `~/tofu/greeting`, cause some drift:
       ```bash
       rm greeting.txt
       ```
    2. [ ] Run `tofu plan` and read what it noticed.
    3. [ ] Run `tofu apply` to repair it.

    **Run** the checks.
    ''', [check('Check the file is back', 'cat $HOME/tofu/greeting/greeting.txt', contains=['Hello, Nagare!']),
          check('Check reality matches the configuration', T('greeting') + ' plan -no-color -detailed-exitcode', contains=['No changes'])],
    'cd ~/tofu/greeting && rm greeting.txt && tofu plan; tofu apply -auto-approve', fails_before=False)

cli('Renaming Resources', '''
    You named a resource badly and want to rename it. If you just change the name in the file, Terraform sees two things:

    - `local_file.greeting` is in the state, but no longer in the code: **destroy it**.
    - `local_file.hello` is in the code, but not in the state: **create it**.

    For a file, fine. For a database, you just deleted production.

    ## Moved

    A `moved` block tells Terraform it's the same thing under a new name:

    ```hcl
    moved {
      from = local_file.greeting
      to   = local_file.hello
    }
    ```

    The plan now shows a rename, and nothing is destroyed:

    ```
      # local_file.greeting has moved to local_file.hello

    Plan: 0 to add, 0 to change, 0 to destroy.
    ```

    ## Assignment

    1. [ ] In `~/tofu/greeting/main.tf`, rename the resource from `"greeting"` to `"hello"`.
    2. [ ] Update the `path` output to use `local_file.hello.filename`.
    3. [ ] Add the `moved` block above.
    4. [ ] Run `tofu plan` and confirm `0 to destroy`, then `tofu apply`.

    **Run** the checks.
    ''', [check('Check the resource was renamed', T('greeting') + ' state list', contains=['local_file.hello'], none=['local_file.greeting']),
          check('Check the file survived', 'cat $HOME/tofu/greeting/greeting.txt', contains=['Hello, Nagare!'])],
    '''
    cd ~/tofu/greeting
    sed -i 's/resource "local_file" "greeting"/resource "local_file" "hello"/; s/local_file.greeting.filename/local_file.hello.filename/' main.tf
    cat >> main.tf <<'EOF'

    moved {
      from = local_file.greeting
      to   = local_file.hello
    }
    EOF
    tofu apply -auto-approve
    ''')

quiz('Remote State', '''
    So far your state is a file in the project folder. That works alone. On a team it falls apart:

    - Everyone needs the latest state, and it shouldn't go in Git.
    - Two people applying at once will corrupt it.

    ## Backends

    A **backend** is where state lives. The default is `local`. Teams use a remote one, such as a cloud storage bucket:

    ```hcl
    terraform {
      backend "s3" {
        bucket = "my-company-tofu-state"
        key    = "web/terraform.tfstate"
        region = "us-east-1"
      }
    }
    ```

    Now everyone, and your CI pipeline, reads and writes the same state. Run `tofu init` after changing a backend.

    ## Locking

    Most backends **lock** the state while someone is planning or applying. A second person gets an error instead of a corrupted file:

    ```
    Error: Error acquiring the state lock
    ```

    ## Secrets

    State stores every attribute of every resource, including passwords, in plain text. So:

    - Keep it in a private, encrypted bucket.
    - Limit who can read it.

    > [!tip]
    > OpenTofu can encrypt the state file itself, before it leaves your machine. That's one of the features Terraform doesn't have built in.
    ''',
    ('Why do teams use a remote backend?',
     'So everyone shares one up-to-date state, with locking to stop simultaneous changes',
     'Because local state files are slower',
     'To avoid running `tofu init`',
     'So the state can be committed to Git safely'),
    ('Two engineers run `tofu apply` on the same project at the same moment, with a locking backend. What happens?',
     'One proceeds. The other gets a state lock error',
     'Both apply, and the state is merged automatically',
     'Both apply, and the later one silently overwrites the first',
     'Neither can ever apply again'))

quiz('Importing', '''
    What about infrastructure that already exists? A server someone created by hand years ago isn't in your state, so Terraform doesn't know about it.

    An `import` block adopts it:

    ```hcl
    import {
      to = aws_instance.web
      id = "i-0abc1234def567890"
    }

    resource "aws_instance" "web" {
      ami           = "ami-0abc1234"
      instance_type = "t3.micro"
    }
    ```

    - `to` is the address in your configuration.
    - `id` is how the platform identifies the real thing. Each resource type documents its own ID format.

    On the next apply, Terraform adds the server to the state **without creating or changing it**. From then on it's managed like anything else.

    You still need a `resource` block that matches the real thing. If they differ, the plan shows the differences, and you fix the code until it shows none.

    ## The Opposite

    To make Terraform forget a resource _without destroying it_:

    ```bash
    tofu state rm aws_instance.web
    ```

    The server keeps running. It just isn't managed any more.
    ''',
    ('What does importing a resource do?',
     'Adds existing infrastructure to the state so Terraform manages it',
     'Creates a copy of the resource',
     'Downloads a provider',
     'Writes the `.tf` code for you and applies it'),
    ('You want Terraform to stop managing a database, but the database must keep running. What do you use?',
     '`tofu state rm`',
     '`tofu destroy`',
     'Delete the resource block, then `tofu apply`',
     '`tofu init`'))

# ------------------------------------------------------------------------------------------------ Loops
chapter('Loops and Logic')

cli('Count', '''
    Need three of something? Don't copy and paste the block three times.

    ```hcl
    resource "local_file" "note" {
      count    = 3
      filename = "note-${count.index}.txt"
      content  = "Note number ${count.index}\\n"
    }
    ```

    `count` makes that many copies. Inside the block, `count.index` is the copy's number, starting at 0.

    The resource is now a list. Each copy has an address with an index:

    ```
    local_file.note[0]
    local_file.note[1]
    local_file.note[2]
    ```

    ## Assignment

    1. [ ] Create a new folder:
       ```bash
       mkdir -p ~/tofu/notes && cd ~/tofu/notes
       ```
    2. [ ] Create `main.tf`:
       ```hcl
       terraform {
         required_providers {
           local = {
             source = "hashicorp/local"
           }
         }
       }

       resource "local_file" "note" {
         count    = 3
         filename = "note-${count.index}.txt"
         content  = "Note number ${count.index}\\n"
       }
       ```
    3. [ ] Run `tofu init` and `tofu apply`.
    4. [ ] Run `ls` and `tofu state list`.

    **Run** the checks.
    ''', [check('Check three notes are in the state', T('notes') + ' state list', contains=['local_file.note[0]', 'local_file.note[1]', 'local_file.note[2]']),
          check('Check the last note', 'cat $HOME/tofu/notes/note-2.txt', contains=['Note number 2'])],
    '''
    mkdir -p ~/tofu/notes && cd ~/tofu/notes
    cat > main.tf <<'EOF'
    TFLOCAL
    resource "local_file" "note" {
      count    = 3
      filename = "note-${count.index}.txt"
      content  = "Note number ${count.index}\\n"
    }
    EOF
    tofu init && tofu apply -auto-approve
    ''')

cli('For Each', '''
    `count` has a trap. Copies are identified by position, so if you remove the one in the middle, everything after it shifts down and gets recreated.

    `for_each` identifies copies by **key** instead. Give it a map:

    ```hcl
    variable "notes" {
      type = map(string)
      default = {
        todo  = "Learn Terraform"
        ideas = "Automate everything"
      }
    }

    resource "local_file" "note" {
      for_each = var.notes
      filename = "${each.key}.txt"
      content  = "${each.value}\\n"
    }
    ```

    Inside the block, `each.key` and `each.value` are the current entry. Addresses use the key:

    ```
    local_file.note["ideas"]
    local_file.note["todo"]
    ```

    Remove `ideas` from the map and only that one file is destroyed. Nothing else moves.

    > [!tip]
    > Use `count` for "N identical things" or an on/off switch. Use `for_each` for everything else.

    ## Assignment

    1. [ ] In `~/tofu/notes/main.tf`, replace the `local_file` resource with the variable and resource above.
    2. [ ] Run `tofu plan`. The three numbered notes are destroyed and two named ones are created.
    3. [ ] Run `tofu apply`, then `ls`.

    **Run** the checks.
    ''', [check('Check the notes are keyed by name', T('notes') + ' state list',
                contains=['local_file.note["todo"]', 'local_file.note["ideas"]'], none=['local_file.note[0]']),
          check('Check a note', 'cat $HOME/tofu/notes/todo.txt', contains=['Learn Terraform'])],
    '''
    cd ~/tofu/notes
    cat > main.tf <<'EOF'
    TFLOCAL
    variable "notes" {
      type = map(string)
      default = {
        todo  = "Learn Terraform"
        ideas = "Automate everything"
      }
    }

    resource "local_file" "note" {
      for_each = var.notes
      filename = "${each.key}.txt"
      content  = "${each.value}\\n"
    }
    EOF
    tofu apply -auto-approve
    ''')

quiz('Conditionals', '''
    HCL has one conditional, and it's an expression:

    ```hcl
    condition ? value_if_true : value_if_false
    ```

    ```hcl
    instance_type = var.environment == "prod" ? "t3.large" : "t3.micro"
    ```

    Big server in production, small one everywhere else.

    ## Optional Resources

    There's no `if` around a block. To make a resource optional, combine a conditional with `count`:

    ```hcl
    variable "create_backup" {
      type    = bool
      default = false
    }

    resource "local_file" "backup" {
      count    = var.create_backup ? 1 : 0
      filename = "backup.txt"
      content  = "backup"
    }
    ```

    `count = 0` means the resource doesn't exist. `count = 1` means one copy, at `local_file.backup[0]`.

    ## Operators

    - Compare: `==`, `!=`, `<`, `>`, `<=`, `>=`
    - Combine: `&&` (and), `||` (or), `!` (not)
    ''',
    ('`count = var.enabled ? 1 : 0`, and `var.enabled` is `false`. How many copies are created?',
     '0',
     '1',
     '2',
     'An error: count cannot be 0'),
    ('What is `var.env == "prod" ? 3 : 1` when `var.env` is `"dev"`?',
     '1',
     '3',
     '`"dev"`',
     '`false`'))

cli('Functions and For Expressions', '''
    ## Functions

    HCL has built-in functions for strings, numbers, and collections. You can't define your own.

    ```hcl
    upper("hello")           # "HELLO"
    length(["a", "b"])       # 2
    join("-", ["a", "b"])    # "a-b"
    max(3, 9, 5)             # 9
    keys({ a = 1, b = 2 })   # ["a", "b"]
    ```

    ## Console

    `tofu console` is a prompt for trying expressions against your real configuration. Leave with `exit`.

    ```
    > upper("hello")
    "HELLO"
    > length(var.notes)
    2
    ```

    ## For Expressions

    A `for` expression turns one collection into another:

    ```hcl
    [for name, text in var.notes : upper(name)]
    ```

    "For each entry in `var.notes`, give me the name in capitals." Square brackets make a list. Maps are walked in key order, so the result is `["IDEAS", "TODO"]`.

    ## Assignment

    1. [ ] In `~/tofu/notes`, run `tofu console` and try `upper("hello")` and `length(var.notes)`. Type `exit` to leave.
    2. [ ] Add this output to `main.tf`:
       ```hcl
       output "titles" {
         value = [for name, text in var.notes : upper(name)]
       }
       ```
    3. [ ] Run `tofu apply`.

    **Run** the checks.
    ''', [check('Check the titles output', T('notes') + ' output -json titles', jq=('join(",")', 'IDEAS,TODO'))],
    '''
    cd ~/tofu/notes
    cat >> main.tf <<'EOF'

    output "titles" {
      value = [for name, text in var.notes : upper(name)]
    }
    EOF
    tofu apply -auto-approve
    ''')

cli('Data Sources', '''
    A resource is something Terraform **manages**. A **data source** is something Terraform only **reads**.

    ```hcl
    data "local_file" "version" {
      filename = "version.txt"
    }
    ```

    This reads a file that already exists. Terraform will never create, change, or delete it.

    References start with `data.`:

    ```hcl
    data.local_file.version.content
    ```

    In real projects, data sources look things up: the newest OS image, the current account ID, a network another team owns. You use the answer without taking ownership of the thing.

    ## Assignment

    1. [ ] In `~/tofu/notes`, create a file by hand. Terraform doesn't manage this one:
       ```bash
       echo "v1.2.3" > version.txt
       ```
    2. [ ] Add this to `main.tf`:
       ```hcl
       data "local_file" "version" {
         filename = "version.txt"
       }

       output "version" {
         value = trimspace(data.local_file.version.content)
       }
       ```
    3. [ ] Run `tofu apply`. The plan adds an output and no resources.

    **Run** the checks.
    ''', [check('Check the version output', T('notes') + ' output -raw version', contains=['v1.2.3']),
          check('Check the file is read, not managed', T('notes') + ' state list', contains=['data.local_file.version'])],
    '''
    cd ~/tofu/notes
    echo "v1.2.3" > version.txt
    cat >> main.tf <<'EOF'

    data "local_file" "version" {
      filename = "version.txt"
    }

    output "version" {
      value = trimspace(data.local_file.version.content)
    }
    EOF
    tofu apply -auto-approve
    ''')

# ------------------------------------------------------------------------------------------------ Modules
chapter('Modules')

quiz('What Is a Module?', '''
    A **module** is a folder of `.tf` files. That's it. You've been writing modules this whole time.

    - The folder where you run `tofu` is the **root module**.
    - A module that another module calls is a **child module**.

    Modules are Terraform's functions:

    | Function      | Module           |
    | ------------- | ---------------- |
    | Parameters    | Variables        |
    | Body          | Resources        |
    | Return values | Outputs          |

    ## Calling a Module

    ```hcl
    module "blog" {
      source = "./modules/website"

      domain = "blog.example.com"
    }
    ```

    - `source` is where the module's files are.
    - Every other argument sets one of the module's variables.

    Call the same module again with different values and you get a second, independent copy. Write "a website" once, then stamp out ten.
    ''',
    ('What is a module?',
     'A folder of `.tf` files that can be called with different inputs',
     'A plugin that talks to a cloud API',
     'A file that stores what Terraform created',
     'A special kind of variable'),
    ('How do you pass a value into a module?',
     "As an argument in the `module` block, matching one of the module's variables",
     'By editing the files inside the module',
     'With an `output` block in the module',
     'Modules cannot take inputs'))

cli('Writing a Module', '''
    Let's build a module that makes a web page, then use it twice.

    A module is used from another folder, so paths need care:

    - `path.module` is the folder of the module the code is in.
    - `path.root` is the folder of the root module.

    ## Assignment

    1. [ ] Create a project with a module folder inside it:
       ```bash
       mkdir -p ~/tofu/site/modules/page && cd ~/tofu/site
       ```
    2. [ ] Create the module, `modules/page/main.tf`:
       ```hcl
       variable "title" {
         type = string
       }

       resource "local_file" "page" {
         filename = "${path.root}/${var.title}.html"
         content  = "<h1>${var.title}</h1>\\n"
       }

       output "path" {
         value = local_file.page.filename
       }
       ```
    3. [ ] Create the root module, `main.tf`, which calls it twice:
       ```hcl
       module "home" {
         source = "./modules/page"
         title  = "home"
       }

       module "about" {
         source = "./modules/page"
         title  = "about"
       }
       ```
    4. [ ] Run `tofu init`. It installs modules as well as providers.
    5. [ ] Run `tofu apply`, then `tofu state list`.

    Notice the addresses: `module.home.local_file.page`. One block of code, two separate resources.

    **Run** the checks.
    ''', [check('Check both module copies exist', T('site') + ' state list', contains=['module.home.local_file.page', 'module.about.local_file.page']),
          check('Check a page', 'cat $HOME/tofu/site/about.html', contains=['<h1>about</h1>'])],
    '''
    mkdir -p ~/tofu/site/modules/page && cd ~/tofu/site
    cat > modules/page/main.tf <<'EOF'
    variable "title" {
      type = string
    }

    resource "local_file" "page" {
      filename = "${path.root}/${var.title}.html"
      content  = "<h1>${var.title}</h1>\\n"
    }

    output "path" {
      value = local_file.page.filename
    }
    EOF
    cat > main.tf <<'EOF'
    module "home" {
      source = "./modules/page"
      title  = "home"
    }

    module "about" {
      source = "./modules/page"
      title  = "about"
    }
    EOF
    tofu init && tofu apply -auto-approve
    ''')

cli('Module Outputs', '''
    A module is a sealed box. From outside, you can't reach the resources inside it:

    ```hcl
    module.home.local_file.page.filename   # not allowed
    ```

    You can only read what the module chooses to expose as an **output**:

    ```hcl
    module.<NAME>.<OUTPUT>
    ```

    Your `page` module has an output called `path`, so the root module can use `module.home.path`.

    That's deliberate. The module's author can rearrange its insides freely, as long as the variables and outputs stay the same.

    A module's outputs aren't printed by `tofu apply`. Only the **root** module's outputs are. To show one, pass it along.

    ## Assignment

    1. [ ] Add this to `~/tofu/site/main.tf`:
       ```hcl
       output "pages" {
         value = [module.home.path, module.about.path]
       }
       ```
    2. [ ] Run `tofu apply`.

    **Run** the checks.
    ''', [check('Check the pages output lists both pages', T('site') + ' output -json pages', jq=('length', 2))],
    '''
    cd ~/tofu/site
    cat >> main.tf <<'EOF'

    output "pages" {
      value = [module.home.path, module.about.path]
    }
    EOF
    tofu apply -auto-approve
    ''')

quiz('The Registry', '''
    You don't have to write every module yourself. Public registries host thousands of them, for almost anything you'd build in the cloud.

    ```hcl
    module "vpc" {
      source  = "terraform-aws-modules/vpc/aws"
      version = "~> 5.0"

      name = "main"
      cidr = "10.0.0.0/16"
    }
    ```

    One block, and you get a complete network that would take hundreds of lines by hand.

    ## Sources

    | Source               | Example                                              |
    | -------------------- | ---------------------------------------------------- |
    | Local folder         | `./modules/page`                                     |
    | Registry             | `terraform-aws-modules/vpc/aws`                      |
    | Git repository       | `git::https://github.com/acme/modules.git?ref=v1.2.0` |

    Terraform downloads from `registry.terraform.io`. OpenTofu downloads from `registry.opentofu.org`. Most modules are in both.

    ## Pin Your Versions

    Without a `version`, you get whatever is newest each time you run `init` somewhere new. Pin it, the same way you pin providers.

    > [!warning]
    > A module is someone else's code, running with your cloud credentials. Read it before you use it.
    ''',
    ('Why set `version` on a registry module?',
     "So a new release can't change your infrastructure unexpectedly",
     'Modules without a version are not downloaded',
     'It makes `tofu apply` faster',
     'It is required for local folder modules'),
    ('Which `source` refers to a module in a folder of your own project?',
     '`./modules/page`',
     '`terraform-aws-modules/vpc/aws`',
     '`hashicorp/local`',
     '`git::https://github.com/acme/modules.git`'))

# ------------------------------------------------------------------------------------------------ Real world
chapter('Working Safely')

cli('Saved Plans', '''
    There's a gap in `tofu apply`. Between reading the plan and typing `yes`, something could change. And in a CI pipeline, nobody is there to type `yes` at all.

    The fix is to save the plan to a file, then apply exactly that file:

    ```bash
    tofu plan -out=tfplan   # save the plan
    tofu show tfplan        # read it
    tofu apply tfplan       # apply exactly what was saved
    ```

    Applying a saved plan doesn't ask for confirmation, because the plan _is_ the approval. If the state has changed since the plan was made, the apply refuses to run.

    This is how teams run Terraform:

    1. A pull request runs `tofu plan -out=tfplan` and posts the result.
    2. A teammate reviews the plan.
    3. After merge, the pipeline runs `tofu apply tfplan`.

    ## Assignment

    1. [ ] In `~/tofu/site/main.tf`, add a third page:
       ```hcl
       module "contact" {
         source = "./modules/page"
         title  = "contact"
       }
       ```
    2. [ ] Run `tofu init`. A new `module` block needs it.
    3. [ ] Save a plan, then read it:
       ```bash
       tofu plan -out=tfplan
       tofu show tfplan
       ```
    4. [ ] Apply the saved plan:
       ```bash
       tofu apply tfplan
       ```

    **Run** the checks.
    ''', [check('Check the plan file exists', 'test -f $HOME/tofu/site/tfplan'),
          check('Check the contact page was created', 'cat $HOME/tofu/site/contact.html', contains=['<h1>contact</h1>'])],
    '''
    cd ~/tofu/site
    cat >> main.tf <<'EOF'

    module "contact" {
      source = "./modules/page"
      title  = "contact"
    }
    EOF
    tofu init && tofu plan -out=tfplan && tofu show tfplan && tofu apply tfplan
    ''')

quiz('Lifecycle', '''
    A `lifecycle` block changes how Terraform treats one resource.

    ```hcl
    resource "aws_db_instance" "main" {
      # ...

      lifecycle {
        prevent_destroy = true
      }
    }
    ```

    ## The Three You'll Use

    **`prevent_destroy = true`**

    Any plan that would destroy this resource fails with an error. A seatbelt for databases.

    **`create_before_destroy = true`**

    When a resource must be replaced, Terraform normally destroys the old one first. This flips the order: create the new one, then remove the old. No downtime in between.

    **`ignore_changes = [tags]`**

    Don't treat changes to these arguments as drift. Useful when another system legitimately edits them.

    > [!warning]
    > `prevent_destroy` only works while the block is in your code. Delete the whole resource block and the protection goes with it.
    ''',
    ('A web server must be replaced, and you want no downtime. Which setting helps?',
     '`create_before_destroy = true`',
     '`prevent_destroy = true`',
     '`ignore_changes = all`',
     '`count = 0`'),
    ('A resource has `prevent_destroy = true`. You run `tofu destroy`. What happens?',
     'The command fails with an error, and nothing is destroyed',
     'Everything except that resource is destroyed, silently',
     'The resource is destroyed after a second confirmation',
     'The setting is ignored by `destroy`'))

quiz('Environments', '''
    You'll want the same infrastructure more than once: dev, staging, production. Each needs its **own state**, so a mistake in dev can't touch production.

    ## A Folder per Environment

    The most common layout. Each environment is a small root module that calls the same shared modules with different values:

    ```
    modules/
      app/
    environments/
      dev/
        main.tf      # module "app" { size = "small" }
      prod/
        main.tf      # module "app" { size = "large" }
    ```

    It's explicit. You always know which environment you're in, because you're standing in its folder.

    ## Workspaces

    One folder, several states:

    ```bash
    tofu workspace new staging
    tofu workspace select staging
    tofu workspace list
    ```

    Each workspace has a separate state for the same code. `terraform.workspace` gives you the current name to use in expressions.

    Less code to maintain, but easier to get wrong: nothing on screen tells you that you're about to apply to production.

    ## Rules of Thumb

    - One state per environment. Always.
    - Keep states small. Split by environment, and by area (network, database, app) as you grow. A bad apply can only break what's in its state.
    ''',
    ('Why should dev and production have separate state?',
     "So a change or mistake in one can't affect the other",
     'Because one state file can only hold ten resources',
     'So they can use different versions of HCL',
     'Separate state is required for `tofu fmt`'),
    ('What does a workspace give you?',
     'A separate state for the same configuration',
     'A separate copy of the `.tf` files',
     'A different provider version',
     'A remote backend'))

quiz('Where to Go Next', '''
    You now know the parts of Terraform that people use every day:

    | Concept      | In one line                                           |
    | ------------ | ----------------------------------------------------- |
    | Provider     | A plugin that talks to one platform's API             |
    | Resource     | One thing Terraform manages                           |
    | Data source  | One thing Terraform only reads                        |
    | Variable     | A value passed in                                     |
    | Local        | A value computed inside                               |
    | Output       | A value passed out                                    |
    | Module       | A reusable folder of configuration                    |
    | State        | Terraform's record of what it manages                 |

    And the loop: **write, plan, apply**.

    ## Clean Up

    Practice the last command. In each of `~/tofu/pets`, `~/tofu/greeting`, `~/tofu/notes`, and `~/tofu/site`:

    ```bash
    tofu destroy
    ```

    ## Next Steps

    - **Use a real provider.** Everything you did with files works the same with servers. Take [Learn AWS](/learn/learn-aws) to understand what you'd be creating.
    - **Read provider docs.** Each resource type lists its arguments and attributes. That page is where you'll spend most of your time.
    - **Put it in a pipeline.** Plan on pull requests, apply on merge. See [Learn CI/CD](/learn/learn-ci-cd-github-docker-golang).
    - **Keep the docs close:** [Terraform](https://developer.hashicorp.com/terraform/docs) and [OpenTofu](https://opentofu.org/docs/).
    ''',
    ('Before running `tofu apply` on production, what should you always do?',
     'Read the plan, especially anything being destroyed or replaced',
     'Delete the state file so it starts clean',
     'Run `tofu destroy` first',
     'Skip the plan with `-auto-approve` to save time'))


def build():
    course = {'slug': SLUG, 'title': 'Learn Terraform', 'chapters': CHAPTERS}
    json.dump(course, open(f'{ROOT}/courses/{SLUG}.json', 'w'))
    p = f'{ROOT}/courses/index.json'
    ix = json.load(open(p))
    entry = {'slug': SLUG, 'title': 'Learn Terraform', 'language': 'terraform',
             'description': 'Describe infrastructure in code and build it with one command: providers, resources, variables, state, and modules, hands-on with OpenTofu.',
             'lessons': [l['uuid'] for ch in CHAPTERS for l in ch['lessons']]}
    ix['courses'] = [c for c in ix['courses'] if c['slug'] != SLUG]
    ix['courses'].insert(next(i for i, c in enumerate(ix['courses']) if c['slug'] == 'learn-kubernetes') + 1, entry)
    for path in ix['paths']:
        if path['slug'] == 'devops-python-golang' and SLUG not in path['courses']:
            path['courses'].insert(path['courses'].index('learn-kubernetes') + 1, SLUG)
    json.dump(ix, open(p, 'w'))
    kinds = [l['type'] for ch in CHAPTERS for l in ch['lessons']]
    print(f"{len(kinds)} lessons in {len(CHAPTERS)} chapters: {kinds.count('type_cli')} hands-on, {kinds.count('type_choice')} quizzes")


def test(home):
    sys.path.insert(0, f'{ROOT}/server')
    import grader
    os.makedirs(home)
    env = {**os.environ, 'HOME': home}
    os.environ['HOME'] = home  # the checks expand $HOME
    bad = 0
    for ch in CHAPTERS:
        for l in ch['lessons']:
            if l['type'] != 'type_cli':
                continue
            script, fails_before = SOLUTIONS[l['title']]
            before = grader.run_cli(l['cli'], home, '')['passed']
            p = subprocess.run(['bash', '-ec', script], cwd=home, env=env, capture_output=True, text=True) if script.strip() else None
            after = grader.run_cli(l['cli'], home, '')
            ok = after['passed'] and (not p or p.returncode == 0) and before != fails_before
            bad += not ok
            print(('ok  ' if ok else 'FAIL'), l['title'], '' if ok else f"| before={before} (want {not fails_before}) after={after['passed']} solution rc={p and p.returncode}")
            if not ok:
                print((p.stdout + p.stderr)[-1500:] if p else '')
                for r in after['results']:
                    if r and r['failures']:
                        print('   ', r['failures'], r['output'][-600:])
    print('all hands-on lessons pass' if not bad else f'{bad} failing')
    return bad


if __name__ == '__main__':
    build()
    if sys.argv[1:2] == ['test']:
        sys.exit(test(sys.argv[2]))
