# jqai

Always forgetting the `jq` syntax? Wish you had a magic box that translated your desires to the right syntax? Look no further than `jqai`!

Generate and execute `jq` programs using LLMs. Transform JSON data using natural language descriptions instead of learning complex `jq` syntax.

## Usage

```bash
cat data.json | uvx jqai "get all user names and emails"
```


## Prerequisites

- **jq**: Must be installed on your system. [Install jq](https://jqlang.github.io/jq/download/)
- **API Key**: OpenAI API key or Echo API key

### Setting up API Key

#### Option 1: OpenAI API Key
```bash
export OPENAI_API_KEY="your-openai-api-key"
```

#### Option 2: Echo API (Recommended)
Get an Echo API key at [echo.merit.systems](https://echo.merit.systems/cli-auth?appId=f6e82af0-ddda-47d9-9bb5-a82ffa41ba73):

```bash
export OPENAI_API_KEY="echo_your-echo-api-key"
```

## Usage

jqai works in two modes:

### 1. Piped JSON Mode

Transform JSON data by piping it to `jqai`:

```bash
cat data.json | jqai "get all user names and emails"
```

```bash
curl -s https://api.github.com/users/octocat | jqai "extract login, name, and public repo count"
```

### 2. Command Generation Mode

Generate complete commands that fetch and process data:

```bash
jqai "show the latest 5 issues from simonw/datasette repo"
```

```bash
jqai "get weather data for San Francisco and extract temperature"
```

## Examples

### Basic JSON Transformation

Given a JSON file `users.json`:
```json
{
  "users": [
    {"name": "Alice", "age": 30, "city": "New York"},
    {"name": "Bob", "age": 25, "city": "San Francisco"},
    {"name": "Charlie", "age": 35, "city": "New York"}
  ]
}
```

Extract names and cities:
```bash
cat users.json | jqai "get names and cities of all users"
```

Filter users from New York:
```bash
cat users.json | jqai "show only users from New York"
```

Count users by city:
```bash
cat users.json | jqai "count users by city"
```

### API Data Processing

Process GitHub API data:
```bash
curl -s https://api.github.com/repos/microsoft/vscode/issues | jqai "show issue titles and their authors"
```

Get repository statistics:
```bash
curl -s https://api.github.com/repos/python/cpython | jqai "extract name, stars, forks, and primary language"
```

### Complex Transformations

Group and aggregate data:
```bash
cat sales.json | jqai "group sales by product and sum the amounts"
```

Nested object manipulation:
```bash
cat complex.json | jqai "flatten the nested user profiles and extract email domains"
```

## Command Line Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--model` | `-m` | OpenAI model to use | `gpt-4.1-mini` |
| `--preview-length` | `-p` | Bytes of input for LLM context | `1024` |
| `--output-only` | `-o` | Show generated program only | `False` |
| `--silent` | `-s` | Reduce output verbosity | `True` |
| `--verbose` | `-v` | Show prompts and responses | `False` |

### Examples with Options

Generate program without executing:
```bash
cat data.json | jqai "extract user emails" --output-only
```

Use a different model:
```bash
cat data.json | jqai "complex analysis" --model gpt-4-turbo-preview
```

Verbose mode for debugging:
```bash
cat data.json | jqai "transform data" --verbose
```

## Advanced Usage

### Learning jq

Use `--output-only` to see the generated `jq` programs and learn:

```bash
$ cat users.json | jqai "get names of users over 30" --output-only
.users[] | select(.age > 30) | .name
```

### Custom Preview Length

For large JSON files, adjust the preview length:

```bash
cat large-file.json | jqai "analyze data structure" --preview-length 2048
```

### Combining with Other Tools

Chain with other command-line tools:

```bash
jqai "get latest commits from torvalds/linux" | head -10
```

```bash
cat logs.json | jqai "extract error messages" | grep -i "critical"
```

## How It Works

1. **Input Analysis**: jqai analyzes your natural language description
2. **Context Building**: For piped data, it reads a preview to understand the JSON structure
3. **Program Generation**: Uses LLM to generate an appropriate `jq` program or shell command
4. **Execution**: Runs the generated program with your data

### Piped Mode Flow
```
JSON Data → Preview → LLM → jq Program → Execute → Output
```

### Command Mode Flow
```
Description → LLM → Shell Command → Execute → Output
```

## Error Handling

jqai handles common errors gracefully:

- **Missing API Key**: Clear instructions on how to set up authentication
- **jq Errors**: Passes through `jq` error messages for debugging
- **Network Issues**: Proper error reporting for API calls
- **Broken Pipes**: Handles interrupted output streams

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.

## Troubleshooting

### Common Issues

**"jq: command not found"**
- Install jq: `brew install jq` (macOS) or `apt-get install jq` (Ubuntu)

**"OPENAI_API_KEY environment variable is not set"**
- Set your API key: `export OPENAI_API_KEY="your-key"`
- For Echo API, get a key at [echo.merit.systems](https://echo.merit.systems/cli-auth?appId=f6e82af0-ddda-47d9-9bb5-a82ffa41ba73)

**Generated program doesn't work as expected**
- Use `--verbose` to see the generated program
- Try `--output-only` to inspect the jq syntax
- Provide more specific descriptions in your natural language query

### Getting Help

For more complex queries, try being more specific:

Instead of: "process the data"
Try: "extract user names and count them by department"

Instead of: "fix the JSON"
Try: "remove null values and flatten nested objects"
