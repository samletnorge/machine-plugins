import type {
  RuntimeAttachmentSummary,
  StudioContextSummary
} from './types';

const contextExample: StudioContextSummary = {
  tenant_slug: 'northwind',
  tenant_name: 'Northwind',
  project_slug: 'fuel-ops',
  project_name: 'Fuel Ops',
  environment_name: 'staging',
  environment_status: 'healthy'
};

const attachmentExample: RuntimeAttachmentSummary = {
  context: {
    tenant_id: 'tenant-northwind',
    project_id: 'project-fuel-ops',
    environment_id: 'environment-staging'
  },
  status: 'attached',
  machine_name: 'FuelOpsMachine',
  attached_at: '2026-05-28T16:00:00Z',
  error: null
};

void contextExample;
void attachmentExample;
