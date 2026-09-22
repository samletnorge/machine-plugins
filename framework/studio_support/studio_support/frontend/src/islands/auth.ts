import { mount } from 'svelte';
import DomainPanel from '../components/DomainPanel.svelte';

const target = document.getElementById('auth-island');

if (target) {
  mount(DomainPanel, {
    target,
    props: {
      domain: 'auth',
      title: 'Auth',
      endpoint: target.dataset.endpoint ?? '/_studio/api/auth/keys'
    }
  });
}
