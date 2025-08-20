[![Invoke All Functions](https://github.com/functions-dev/templates/actions/workflows/invoke-all.yaml/badge.svg)](https://github.com/functions-dev/templates/actions/workflows/invoke-all.yaml)
[![License](https://img.shields.io/github/license/functions-dev/templates)](https://github.com/functions-dev/templates/blob/main/LICENSE)

# WELCOME To Knative Function Templates!

## Quick search

1. [Basic Information](#templates-for-knative-functions)
2. [Prerequisites](#prerequisites)
3. [How To Use](#how-to-use)
    1. [Build a Function](#build-a-function)
    2. [Deploy a Function](#deploy-a-function)
4. [Function Templates Structure](#templates-structure)
6. [Contact](#contact)
7. [F&Q](#fq)

## Templates for Knative Functions
This repository showcases some use-cases for your Knative Functions!
It is a collection of function templates. The built-in templates
are either *http* or *cloudevents* and these are custom template overrides.

Templates in this repository include:
- The easiest Hello World (`hello`)
- Simple splash screen with **referenced .css file** and **.funcignore** (`splash`)
- Web blog with **serverside rendering** and **import statements** (`blog`)
- upcoming: A "Contact Us" function with a **secret password** (`contact-us`)

See [templates structure](#templates-structure) to learn about repository and
see how to [deploy](#deploy-a-function) your function.

## Prerequisites
In order to use Functions, you will need a few things:

### Get the `func` binary

#### Build from source
You can clone our [GitHub repository](https://github.com/knative/func/) and
build your binary from the source. You simply run 'make' in the root directory
to obtain the 'func' binary.

#### Download the binary
Download the binary straight from the
[release pages](https://github.com/knative/func/releases) under *Assets*.

Alternatively, for your convenience, see if your OS and architecture can be
found in the list below for an easy copy&paste and download our latest version.

#### Linux

##### amd64
```bash
curl -L -o /usr/local/bin/func https://github.com/knative/func/releases/latest/download/func_linux_amd64
```

##### arm64
```bash
curl -L -o /usr/local/bin/func https://github.com/knative/func/releases/latest/download/func_linux_arm64
```

#### Windows

##### PowerShell
```powershell
Invoke-WebRequest -Uri "https://github.com/knative/func/releases/latest/download/func_windows_amd64.exe" -OutFile <"C:\path\to\your\destination\func.exe">
```
alternatively if `curl` is pre-installed
```powershell
curl -L -o <C:\path\to\your\destination\func.exe> "https://github.com/knative/func/releases/latest/download/func_windows_amd64.exe"
```

> [!WARNING]
> You need to change the part in <> to your desired destination
> (don't include the "<>" symbols)

#### Mac (darwin OS)

##### amd64

```sh
curl -L -o /usr/local/bin/func "https://github.com/knative/func/releases/latest/download/func_darwin_amd64"
```

##### arm64

```sh
curl -L -o /usr/local/bin/func "https://github.com/knative/func/releases/latest/download/func_darwin_arm64"
```

> [!NOTE]
> After downloading on MacOS and Linux, you might need to make the file
> executable

```sh
chmod +x /usr/local/bin/func
```

### Get a containerization technology
These are some open-source examples of what you can use with Functions. You will
need some tools to at least build and push your images. This list is not exhaustive.

[Buildah](https://github.com/containers/buildah/blob/main/install.md) - CLI tool
to build your images.

[Podman](https://podman.io/docs/installation#installing-on-linux) - complementary
to Buildah. Helps you manage and modify your images. Uses Buildah's golang API.
Can be installed independently. (*You can get this as a standalone tool*)

[Docker Engine](https://docs.docker.com/engine/install/) - Helps you build and
containerize your applications. (*You can get this as a standalone tool*)

#### Download local cluster runner (kind)
Please refer to **kind**
[installation page](https://kind.sigs.k8s.io/docs/user/quick-start/#installation)
or download any other runner that you prefer.

#### Download cli commands for k8s (kubectl)
In order to interact with the objects in k8s, its recommended to get
[kubectl](https://kubernetes.io/docs/tasks/tools/).

## How To Use
You use these templates by creating your function via `--repository` flag which
means "create my function from this repository".

Create your functions directory and `cd` into it

```
mkdir -p ~/testing/myfunc && cd ~/testing/myfunc
```

Create a function in **golang** with **hello template** within the new
(current and empty) directory

```
func create --repository=https://github.com/functions-dev/templates --language go --template=hello
```

Alternatively create the directory with it:

```
func create myfunc --repository=https://github.com/functions-dev/templates --language go --template=hello
```

where `--language` conveniently matches the runtime and `--template` matches
it's subdirectory containing the Function template, hence:

```
root
├── go
|    ├── hello
|    |     ├── README.md
|    |     ├── function/
|    |     ├── tests/
|    |     └── go.mod
|    ├── blog
|    |     ├── ...
|    |     ...
├── python
|    ├─ ...
|    ...
```

see detailed info in [Templates structure](#templates-structure) section.

### Build a Function
>[!NOTE]
> This step is optional, you can skip straight to [Deploying](deploy-a-function)
> or [Running](run-a-function)
> 1) If you don't need to do any extra setup. Deploy step already builds for you
> 2) If you already have your own function image built.

#### Using the Host Builder
> [!WARNING]
> Host builder is currently available only for runtimes `go` and `python`

> [!TIP]
> We recommend using the host builder `--builder=host` when available

You build a function using the `func build` command. You can specify your desired
builder (look below) or don't configure anything and use the default.

#### Using Alternative Builders
Alternative built-in builders are `pack` and `s2i` (for supported languages).
The way to use them is simple. Just specify which one you want using the
`--builder` flag (eg. `--builder=pack`)

### Run a Function
If you want to test your function and don't want to constantly deploy to a
cluster you can use `func run` in order to run your function locally, in your
CLI.

You can use `--builder` flag to tell `func` which builder to use as well as
`--address` to specify which address your function should be available at. For
the complete list, please refer to `func run -h`.

### Deploy a Function
> [!WARNING]
> In order to deploy anything to a cluster, you will need to have one set up and
> running along with at least [Knative-Serving](https://knative.dev/docs/serving/)
> installed.

#### Local deployment
You can deploy your local code (from your machine) to a cluster using a standard
deploy command. `func` will need to know a registry to use for the image
*to be created*. You can specify with a flag or wait to be prompted for it.

```bash
func deploy --registry=myregistry.com/username
```

If you already have your image you can also specify it via `--image` flag.
Here you can also specify your `--builder` as well as many other things. Please
refer to `func deploy -h` for the complete list.

```bash
func deploy --image=registry.com/username/myimage@sha256:xxx
```

> [!TIP]
> If you know what you want, at any point you can add a `--build` flag to
> your command which will explicitly tell `func` if you want to build (or not)
> your image. (truthy values will work).

#### Remote deployment

You can also utilize a remote deployment, which will use
[tekton](https://tekton.dev/) under the hood. (Which will need to be present in
your cluster).

You can simply add `--remote` to your `func deploy` command.

We also have the option to deploy from a git repository. You can explore this
via `--git*` flags. And please explore any other flags in `func deploy -h` to
see what is available!

## Templates structure
 Directory structure is as follows: **root/[language]/[template]** where *root* is
 the github repository itself, *language* is the programming language used and
 *template* is the name of the template. Function is created from repo via
 `--repository` flag when using `func create` command. More in
 [How-To-Use](#how-to-use) section.

```
github.com/function-dev/templates <---[root]
├── go <------------------------------[language]
│   ├── hello <-----------------------[template]
│   │   └── <function source files>
│   └── splash-screen
│       └── ...
├── node
│   ├── hello
│   └── splash-screen
├── ...
```

# Contact
You can contact us on CNCF Slack
[knative-functions](https://cloud-native.slack.com/archives/C04LKEZUXEE) channel

## F&Q
1. **Function signature error**
```
Error: function may not implement both the static and instanced method signatures
simultaneously
```
***->** this happens when `func (f *F) Somename(){}` is defined as well as
`func Handle(){}`, these are the 2 signatures supported currently - instanced
and static. You will need to check your source code and remove the signature you
don't want.*
