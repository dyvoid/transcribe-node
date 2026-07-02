# .prompts

Versioned prompts that generated significant code in this project.

When an AI session produces a meaningful chunk of code, save the prompt that drove it here as a
markdown file, and reference it from the commit body:

```
feat(auth): add JWT refresh logic

ai-assisted: <model> | prompt: .prompts/auth-refresh.md
```

This makes significant code reproducible and debuggable: you can see not just what was written, but
what was asked for. Name files after the task, not the date.
