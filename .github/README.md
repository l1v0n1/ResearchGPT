# GitHub Actions for ResearchGPT

This directory contains GitHub Action workflows for the ResearchGPT project.

## AI-ReviewBuddy

AI-ReviewBuddy is installed to provide automated code reviews on pull requests. The bot will analyze code changes and provide helpful suggestions to improve code quality, identify potential issues, and ensure best practices.

### Configuration

The AI-ReviewBuddy is configured in [.github/workflows/ai-review-buddy.yml](../workflows/ai-review-buddy.yml) and will run automatically on:
- New pull requests
- Updates to existing pull requests
- Comments on pull request reviews

### Usage

Simply create a pull request, and AI-ReviewBuddy will automatically review your code changes. The bot will add comments directly on the pull request with suggestions and feedback.

### Permissions

The workflow requires the following permissions:
- `contents: read` - To read the repository contents
- `pull-requests: write` - To comment on pull requests

These permissions are granted through the GitHub token that's automatically provided to all workflows. 