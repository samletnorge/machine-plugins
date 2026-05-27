import assert from 'node:assert/strict';
import { renderMarkdown } from './markdown.ts';

const rendered = renderMarkdown(`## Heading\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n\n1. First\n2. Second`);

assert.match(rendered, /<h2>|<table>|<ol>/);
