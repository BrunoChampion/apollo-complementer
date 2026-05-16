const REVENUE_COPILOT_MENU = 'Revenue Copilot';

const LEADS_HEADERS = [
  'lead_id',
  'company_name',
  'company_website',
  'company_domain',
  'company_linkedin_url',
  'prospect_name',
  'prospect_title',
  'prospect_linkedin_url',
  'prospect_email',
  'country',
  'region',
  'industry',
  'company_size',
  'technologies',
  'annual_revenue',
  'total_funding',
  'latest_funding',
  'latest_funding_amount',
  'apollo_contact_id',
  'apollo_account_id',
  'source',
  'manual_context',
  'manual_company_context',
  'manual_person_context',
  'manual_linkedin_notes',
  'manual_company_linkedin_text',
  'manual_person_linkedin_text',
  'manual_company_linkedin_copied_at',
  'manual_person_linkedin_copied_at',
  'identity_validation_status',
  'identity_validation_reason',
  'icp_status',
  'icp_score',
  'icp_score_reason',
  'ready_for_enrichment',
  'ready_for_draft',
  'source_url',
  'action',
  'status',
  'fit_score',
  'fit_score_reason',
  'quality_score',
  'quality_issues',
  'evidence_quality',
  'enrichment_result',
  'review_required',
  'review_category',
  'review_summary',
  'review_evidence',
  'suggested_action',
  'suggested_action_reason',
  'user_decision',
  'user_decision_notes',
  'manual_context_summary',
  'message_angle',
  'email_subject',
  'email_draft',
  'revision_instruction',
  'revision_instruction_hash',
  'last_processed_revision_hash',
  'revision_count',
  'revised_draft',
  'approved',
  'final_subject',
  'final_message',
  'gmail_draft_id',
  'gmail_draft_url',
  'export_ready',
  'agent_note',
  'error_message',
  'run_id',
  'locked_at',
  'processed_at',
  'last_updated_by_agent_at',
];

const RUNS_HEADERS = [
  'run_id',
  'started_at',
  'finished_at',
  'source',
  'sheet_id',
  'created_by',
  'status',
  'total_rows',
  'success_count',
  'error_count',
  'skipped_count',
  'drafts_created',
  'batch_limit',
  'notes',
];

const EMAIL_DRAFTS_HEADERS = [
  'run_id',
  'lead_id',
  'created_at',
  'company_name',
  'prospect_name',
  'prospect_title',
  'prospect_email',
  'email_subject',
  'gmail_draft_id',
  'gmail_draft_url',
  'approved',
  'sent_manually',
  'sent_at',
  'reply_status',
  'notes',
];

const IMPORTS_HEADERS = [
  'import_batch_id',
  'source_provider',
  'source_type',
  'file_name',
  'created_by',
  'created_at',
  'total_rows',
  'imported_count',
  'duplicate_count',
  'rejected_count',
  'error_count',
  'status',
  'notes',
];

const SOURCE_CANDIDATES_HEADERS = [
  'candidate_id',
  'source_provider',
  'source_record_id',
  'source_url',
  'company_name',
  'company_website',
  'company_domain',
  'company_linkedin_url',
  'prospect_name',
  'prospect_title',
  'prospect_linkedin_url',
  'prospect_email',
  'country',
  'region',
  'industry',
  'company_size',
  'raw_headline',
  'raw_company_description',
  'raw_data_json',
  'candidate_status',
  'candidate_score',
  'candidate_score_reason',
  'apollo_enrichment_status',
  'apollo_enrichment_reason',
  'apollo_enrichment_score',
  'apollo_enrichment_confidence',
  'apollo_email_enriched_at',
  'apollo_credits_used',
  'manual_company_linkedin_text',
  'manual_person_linkedin_text',
  'manual_company_linkedin_copied_at',
  'manual_person_linkedin_copied_at',
  'identity_validation_status',
  'identity_validation_reason',
  'icp_status',
  'icp_score',
  'icp_score_reason',
  'ready_for_enrichment',
  'ready_for_draft',
  'dedupe_key',
  'duplicate_of',
  'import_batch_id',
  'created_at',
  'reviewed_by',
  'reviewed_at',
  'notes',
];

const ENRICHMENT_HEADERS = [
  'enrichment_id',
  'run_id',
  'lead_id',
  'company_name',
  'company_website',
  'company_domain',
  'company_linkedin_url',
  'prospect_name',
  'prospect_title',
  'prospect_linkedin_url',
  'country',
  'industry',
  'company_size',
  'enrichment_status',
  'company_summary',
  'b2b_fit',
  'operational_pain_hypothesis',
  'possible_ai_use_case',
  'personalization_angle',
  'trigger_summary',
  'risk_flags',
  'review_required',
  'review_category',
  'review_summary',
  'review_evidence',
  'suggested_action',
  'suggested_action_reason',
  'user_decision',
  'user_decision_notes',
  'evidence_count',
  'evidence_sources',
  'evidence_summary',
  'evidence_urls',
  'confidence_score',
  'recommended_action',
  'created_at',
  'finished_at',
  'error_message',
];

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu(REVENUE_COPILOT_MENU)
    .addItem('Configurar plantilla', 'setupRevenueCopilotTemplate')
    .addItem('Procesar pendientes', 'processPendingRows')
    .addItem('Crear borradores Gmail aprobados', 'createApprovedGmailDrafts')
    .addItem('Exportar CSV', 'exportCsv')
    .addSeparator()
    .addItem('1. Importar export Apollo', 'importCandidatesFromTempTab')
    .addItem('2. Validar LinkedIn + ICP', 'validateSelectedCandidates')
    .addItem('3. Promover candidatos validados', 'promoteSelectedCandidates')
    .addItem('4. Enriquecer leads listos', 'enrichPendingLeads')
    .addItem('5. Generar drafts enriquecidos', 'draftEnrichedLeads')
    .addItem('Sincronizar Enrichment desde Leads', 'syncEnrichmentFromLeads')
    .addItem('Revisar draft enriquecido', 'reviseEnrichedDrafts')
    .addToUi();
}

function setupRevenueCopilotTemplate() {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  ensureSheetWithHeaders(spreadsheet, 'Leads', LEADS_HEADERS);
  ensureSheetWithHeaders(spreadsheet, 'Runs', RUNS_HEADERS);
  ensureSheetWithHeaders(spreadsheet, 'Email Drafts', EMAIL_DRAFTS_HEADERS);
  ensureSheetWithHeaders(spreadsheet, 'Imports', IMPORTS_HEADERS);
  ensureSheetWithHeaders(spreadsheet, 'Source Candidates', SOURCE_CANDIDATES_HEADERS);
  ensureSheetWithHeaders(spreadsheet, 'Enrichment', ENRICHMENT_HEADERS);
  setupLeadDecisionValidation_(spreadsheet);
  spreadsheet.toast('Plantilla Revenue Copilot lista', REVENUE_COPILOT_MENU, 8);
}

function ensureSheetWithHeaders(spreadsheet, sheetName, headers) {
  let sheet = spreadsheet.getSheetByName(sheetName);
  if (!sheet) {
    sheet = spreadsheet.insertSheet(sheetName);
  }
  const existingHeaders = sheet.getRange(1, 1, 1, Math.max(sheet.getLastColumn(), headers.length)).getValues()[0];
  const existingSet = new Set(existingHeaders.filter(String));
  const mergedHeaders = existingHeaders.filter(String);
  headers.forEach((header) => {
    if (!existingSet.has(header)) {
      mergedHeaders.push(header);
    }
  });
  sheet.getRange(1, 1, 1, mergedHeaders.length).setValues([mergedHeaders]);
  sheet.setFrozenRows(1);
}

function setupLeadDecisionValidation_(spreadsheet) {
  const sheet = spreadsheet.getSheetByName('Leads');
  if (!sheet) return;
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  const column = headers.indexOf('user_decision') + 1;
  if (!column) return;
  const rule = SpreadsheetApp.newDataValidation()
    .requireValueInList(
      ['approve_exception', 'pause', 'discard', 'change_target', 'needs_more_context'],
      true
    )
    .setAllowInvalid(false)
    .build();
  sheet.getRange(2, column, Math.max(sheet.getMaxRows() - 1, 1), 1).setDataValidation(rule);
}

function processPendingRows() {
  startRevenueCopilotRun('google_sheets');
}

function createApprovedGmailDrafts() {
  startRevenueCopilotRun('google_sheets');
}

function exportCsv() {
  startRevenueCopilotRun('google_sheets');
}

function importCandidatesFromTempTab() {
  const ui = SpreadsheetApp.getUi();
  const result = ui.prompt(
    'Importar candidatos CSV',
    'Nombre de la tab temporal (default: CSV Import Temp):',
    ui.ButtonSet.OK_CANCEL
  );
  if (result.getSelectedButton() !== ui.Button.OK) return;
  const tempTabName = result.getResponseText().trim() || 'CSV Import Temp';

  const result2 = ui.prompt(
    'Proveedor de datos',
    'Provider (apollo, snov, hunter, findymail, generic):',
    ui.ButtonSet.OK_CANCEL
  );
  if (result2.getSelectedButton() !== ui.Button.OK) return;
  const provider = result2.getResponseText().trim() || 'generic';

  callRevenueCopilotApi('/imports/from_sheet_tab', {
    source_provider: provider,
    temp_tab_name: tempTabName,
    source: 'google_sheets',
    sheet_id: SpreadsheetApp.getActiveSpreadsheet().getId(),
    created_by: Session.getActiveUser().getEmail(),
    promote_to_leads: false,
  });
}

function promoteSelectedCandidates() {
  const ui = SpreadsheetApp.getUi();
  const result = ui.prompt(
    'Promover candidatos',
    'IDs de candidatos separados por coma (dejar vacio para promover todos):',
    ui.ButtonSet.OK_CANCEL
  );
  if (result.getSelectedButton() !== ui.Button.OK) return;
  const input = result.getResponseText().trim();
  const candidateIds = input ? input.split(',').map(s => s.trim()) : null;

  callRevenueCopilotApi('/candidates/promote', {
    source: 'google_sheets',
    sheet_id: SpreadsheetApp.getActiveSpreadsheet().getId(),
    candidate_ids: candidateIds,
  });
}

function validateSelectedCandidates() {
  const ui = SpreadsheetApp.getUi();
  const result = ui.prompt(
    'Validar LinkedIn + ICP',
    'IDs de candidatos separados por coma (dejar vacio para validar todos):',
    ui.ButtonSet.OK_CANCEL
  );
  if (result.getSelectedButton() !== ui.Button.OK) return;
  const input = result.getResponseText().trim();
  const candidateIds = input ? input.split(',').map(s => s.trim()) : null;

  callRevenueCopilotApi('/candidates/validate', {
    source: 'google_sheets',
    sheet_id: SpreadsheetApp.getActiveSpreadsheet().getId(),
    candidate_ids: candidateIds,
  });
}

function enrichPendingLeads() {
  const payload = buildEnrichmentPayload_('Enriquecer leads listos', {
    requireSelection: true,
    maxSelection: 3,
  });
  if (!payload) return;
  callRevenueCopilotApi('/enrichment/run', payload);
}

function draftEnrichedLeads() {
  const payload = buildEnrichmentPayload_('Generar drafts enriquecidos', {
    requireSelection: true,
    maxSelection: 5,
  });
  if (!payload) return;
  callRevenueCopilotApi('/enrichment/draft', payload);
}

function enrichAndDraftLeads() {
  const ui = SpreadsheetApp.getUi();
  ui.alert(
    'Flujo combinado deshabilitado',
    'Primero usa Enriquecer leads listos y luego Generar drafts enriquecidos. Esto evita redactar con contexto incompleto.',
    ui.ButtonSet.OK
  );
}

function buildEnrichmentPayload_(title, options) {
  options = options || {};
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  const selection = getSelectedLeadSelection_();
  const payload = {
    source: 'google_sheets',
    sheet_id: spreadsheet.getId(),
    tab_name: 'Leads',
  };

  const ui = SpreadsheetApp.getUi();
  if (options.requireSelection && !selection.leadIds.length) {
    ui.alert(
      title,
      'Selecciona primero las filas de Leads que quieres procesar. Para evitar timeouts de ngrok/Sheets, no se procesan todos los leads en una sola llamada.',
      ui.ButtonSet.OK
    );
    return null;
  }
  if (
    options.maxSelection &&
    selection.leadIds.length &&
    selection.leadIds.length > options.maxSelection
  ) {
    ui.alert(
      title,
      `Selecciona maximo ${options.maxSelection} fila(s) por corrida. Procesar lotes pequenos evita timeouts y facilita revisar resultados.`,
      ui.ButtonSet.OK
    );
    return null;
  }

  if (selection.leadIds.length) {
    const response = ui.alert(
      title,
      `Seleccionaste ${selection.leadIds.length} fila(s) en ${selection.sheetName}. Presiona Yes para volver a procesarlas aunque ya tengan resultado. Presiona No para procesarlas solo si estan pendientes.`,
      ui.ButtonSet.YES_NO_CANCEL
    );
    if (response === ui.Button.CANCEL) return;
    payload.lead_ids = selection.leadIds;
    if (response === ui.Button.YES && selection.leadIds.length > 3) {
      ui.alert('Selecciona maximo 3 filas para reprocesar. Esto ayuda a controlar costo y tiempo.');
      return null;
    }
    payload.run_id = response === ui.Button.YES
      ? `manual_reprocess_${new Date().toISOString()}`
      : `manual_selected_${new Date().toISOString()}`;
    payload.force = response === ui.Button.YES;
  }
  return payload;
}

function syncEnrichmentFromLeads() {
  callRevenueCopilotApi('/enrichment/sync_from_leads', {
    source: 'google_sheets',
    sheet_id: SpreadsheetApp.getActiveSpreadsheet().getId(),
    tab_name: 'Leads',
  });
}

function reviseEnrichedDrafts() {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  const leadIds = getSelectedLeadIds_();
  callRevenueCopilotApi('/enrichment/revise', {
    source: 'google_sheets',
    sheet_id: spreadsheet.getId(),
    tab_name: 'Leads',
    lead_ids: leadIds.length ? leadIds : null,
    run_id: `manual_revise_${new Date().toISOString()}`,
  });
}

function getSelectedLeadIds_() {
  return getSelectedLeadSelection_().leadIds;
}

function getSelectedLeadSelection_() {
  const sheet = SpreadsheetApp.getActiveSheet();
  const sheetName = sheet ? sheet.getName() : '';
  if (!sheet) return { sheetName, leadIds: [] };
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  const leadIdColumn = headers.indexOf('lead_id') + 1;
  if (!leadIdColumn) return { sheetName, leadIds: [] };

  let ranges = [];
  const rangeList = sheet.getActiveRangeList();
  if (rangeList) {
    ranges = rangeList.getRanges();
  } else {
    const range = sheet.getActiveRange();
    if (range) ranges = [range];
  }
  if (!ranges.length) return { sheetName, leadIds: [] };

  const seen = new Set();
  const leadIds = [];
  ranges.forEach((range) => {
    const startRow = range.getRow();
    const numRows = range.getNumRows();
    if (startRow === 1 && numRows === 1) return;
    const firstDataRow = Math.max(startRow, 2);
    const rowsToRead = numRows - (firstDataRow - startRow);
    if (rowsToRead <= 0) return;
    const ids = sheet
      .getRange(firstDataRow, leadIdColumn, rowsToRead, 1)
      .getValues()
      .flat()
      .filter(String);
    ids.forEach((id) => {
      const normalized = String(id).trim();
      if (!normalized || seen.has(normalized)) return;
      seen.add(normalized);
      leadIds.push(normalized);
    });
  });
  return { sheetName, leadIds };
}

function callRevenueCopilotApi(endpoint, payload) {
  const properties = PropertiesService.getScriptProperties();
  const apiBaseUrl = properties.getProperty('REVENUE_COPILOT_API_BASE_URL');
  const sharedSecret = properties.getProperty('REVENUE_COPILOT_SHARED_SECRET');
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();

  if (!apiBaseUrl) {
    throw new Error('Missing Script Property: REVENUE_COPILOT_API_BASE_URL');
  }

  const response = UrlFetchApp.fetch(`${apiBaseUrl}${endpoint}`, {
    method: 'post',
    contentType: 'application/json',
    muteHttpExceptions: true,
    headers: {
      'X-Revenue-Copilot-Secret': sharedSecret || '',
    },
    payload: JSON.stringify(payload),
  });

  const statusCode = response.getResponseCode();
  const body = response.getContentText();
  if (statusCode < 200 || statusCode >= 300) {
    throw new Error(`Revenue Copilot API error ${statusCode}: ${body}`);
  }

  const result = JSON.parse(body);
  spreadsheet.toast(`OK: ${endpoint} - procesados: ${result.processed_count || result.promoted_count || result.imported_count || result.validated_count || 'ok'}`, REVENUE_COPILOT_MENU, 8);
  return result;
}

function startRevenueCopilotRun(source) {
  const properties = PropertiesService.getScriptProperties();
  const apiBaseUrl = properties.getProperty('REVENUE_COPILOT_API_BASE_URL');
  const sharedSecret = properties.getProperty('REVENUE_COPILOT_SHARED_SECRET');
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = spreadsheet.getActiveSheet();

  if (!apiBaseUrl) {
    throw new Error('Missing Script Property: REVENUE_COPILOT_API_BASE_URL');
  }

  const response = UrlFetchApp.fetch(`${apiBaseUrl}/runs`, {
    method: 'post',
    contentType: 'application/json',
    muteHttpExceptions: true,
    headers: {
      'X-Revenue-Copilot-Secret': sharedSecret || '',
    },
    payload: JSON.stringify({
      source,
      sheet_id: spreadsheet.getId(),
      tab_name: sheet.getName(),
      created_by: Session.getActiveUser().getEmail(),
      process_async: true,
    }),
  });

  const statusCode = response.getResponseCode();
  const body = response.getContentText();
  if (statusCode < 200 || statusCode >= 300) {
    throw new Error(`Revenue Copilot API error ${statusCode}: ${body}`);
  }

  const result = JSON.parse(body);
  spreadsheet.toast(`Procesamiento iniciado: ${result.run_id}`, REVENUE_COPILOT_MENU, 8);
}
