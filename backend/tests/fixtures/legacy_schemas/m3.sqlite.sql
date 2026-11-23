-- Schema created by create_all() at commit 7537614 (scripts/make-legacy-schema-fixtures.sh)
CREATE TABLE assisted_setup_requests (
	id VARCHAR(36) NOT NULL, 
	workspace_id VARCHAR(36) NOT NULL, 
	provider VARCHAR(30) NOT NULL, 
	note VARCHAR(300) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	created_at VARCHAR(48) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES saas_workspaces (id)
);
CREATE TABLE campaign_import_runs (
	id INTEGER NOT NULL, 
	workspace_id VARCHAR(36) DEFAULT 'public-demo' NOT NULL, 
	processed_at VARCHAR(40) NOT NULL, 
	campaigns_inserted INTEGER NOT NULL, 
	redemptions_inserted INTEGER NOT NULL, 
	duplicates INTEGER NOT NULL, 
	rejected INTEGER NOT NULL, 
	issues_json TEXT NOT NULL, 
	PRIMARY KEY (id)
);
CREATE TABLE campaign_redemptions (
	id INTEGER NOT NULL, 
	workspace_id VARCHAR(36) DEFAULT 'public-demo' NOT NULL, 
	redemption_id VARCHAR(120) NOT NULL, 
	campaign_id VARCHAR(80) NOT NULL, 
	provider VARCHAR(20) NOT NULL, 
	source_order_id VARCHAR(120) NOT NULL, 
	redeemed_at VARCHAR(40) NOT NULL, 
	discount_minor INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_workspace_redemption UNIQUE (workspace_id, redemption_id), 
	CONSTRAINT uq_workspace_one_campaign_per_order UNIQUE (workspace_id, provider, source_order_id)
);
CREATE TABLE campaigns (
	workspace_id VARCHAR(36) DEFAULT 'public-demo' NOT NULL, 
	campaign_id VARCHAR(80) NOT NULL, 
	code VARCHAR(80) NOT NULL, 
	name VARCHAR(160) NOT NULL, 
	offer_type VARCHAR(30) NOT NULL, 
	start_date VARCHAR(10) NOT NULL, 
	end_date VARCHAR(10) NOT NULL, 
	variable_cost_minor INTEGER NOT NULL, 
	fixed_cost_minor INTEGER NOT NULL, 
	description TEXT NOT NULL, 
	PRIMARY KEY (workspace_id, campaign_id)
);
CREATE TABLE canonical_orders (
	id INTEGER NOT NULL, 
	workspace_id VARCHAR(36) DEFAULT 'public-demo' NOT NULL, 
	provider VARCHAR(20) NOT NULL, 
	source_order_id VARCHAR(120) NOT NULL, 
	location_id VARCHAR(120) NOT NULL, 
	created_at VARCHAR(80) NOT NULL, 
	customer_id VARCHAR(120), 
	net_sales_minor INTEGER NOT NULL, 
	discount_minor INTEGER NOT NULL, 
	refund_minor INTEGER NOT NULL, 
	payload_json TEXT NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_workspace_provider_order UNIQUE (workspace_id, provider, source_order_id)
);
CREATE TABLE import_runs (
	id INTEGER NOT NULL, 
	workspace_id VARCHAR(36) DEFAULT 'public-demo' NOT NULL, 
	provider VARCHAR(20) NOT NULL, 
	processed_at VARCHAR(40) NOT NULL, 
	inserted INTEGER NOT NULL, 
	duplicates INTEGER NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	PRIMARY KEY (id)
);
CREATE TABLE local_sessions (
	token_hash VARCHAR(64) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	csrf_token VARCHAR(100) NOT NULL, 
	created_at INTEGER NOT NULL, 
	expires_at INTEGER NOT NULL, 
	PRIMARY KEY (token_hash), 
	FOREIGN KEY(user_id) REFERENCES local_users (id)
);
CREATE TABLE local_users (
	id VARCHAR(36) NOT NULL, 
	email VARCHAR(254) NOT NULL, 
	password_hash VARCHAR(320) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id)
);
CREATE TABLE saas_billing_events (
	stripe_event_id VARCHAR(160) NOT NULL, 
	processed_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (stripe_event_id)
);
CREATE TABLE saas_workspace_demo_orders (
	id INTEGER NOT NULL, 
	workspace_id VARCHAR(36) NOT NULL, 
	provider VARCHAR(20) NOT NULL, 
	source_order_id VARCHAR(140) NOT NULL, 
	location_id VARCHAR(120) NOT NULL, 
	created_at VARCHAR(80) NOT NULL, 
	status VARCHAR(35) NOT NULL, 
	customer_id VARCHAR(140), 
	net_sales_minor INTEGER NOT NULL, 
	discount_minor INTEGER NOT NULL, 
	campaign_code VARCHAR(100), 
	campaign_discount_minor INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_saas_demo_order UNIQUE (workspace_id, provider, source_order_id), 
	FOREIGN KEY(workspace_id) REFERENCES saas_workspaces (id)
);
CREATE TABLE saas_workspaces (
	id VARCHAR(36) NOT NULL, 
	owner_sub VARCHAR(160) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	restaurant_type VARCHAR(35) NOT NULL, 
	goal VARCHAR(40) NOT NULL, 
	subscription_plan VARCHAR(20) NOT NULL, 
	subscription_status VARCHAR(35) NOT NULL, 
	stripe_customer_id VARCHAR(120), 
	stripe_subscription_id VARCHAR(120), 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (stripe_customer_id), 
	UNIQUE (stripe_subscription_id)
);
CREATE TABLE sandbox_monitored_locations (
	workspace_id VARCHAR(36) NOT NULL, 
	location_id VARCHAR(160) NOT NULL, 
	merchant_id VARCHAR(160) NOT NULL, 
	name VARCHAR(160) NOT NULL, 
	selected_at VARCHAR(48) NOT NULL, 
	PRIMARY KEY (workspace_id, location_id), 
	FOREIGN KEY(workspace_id) REFERENCES saas_workspaces (id)
);
CREATE TABLE square_location_state (
	workspace_id VARCHAR(36) NOT NULL, 
	location_id VARCHAR(160) NOT NULL, 
	name VARCHAR(160) NOT NULL, 
	timezone VARCHAR(64) NOT NULL, 
	backfill_start VARCHAR(32) NOT NULL, 
	synced_through VARCHAR(32), 
	backfill_complete BOOLEAN NOT NULL, 
	updated_at VARCHAR(48) NOT NULL, 
	PRIMARY KEY (workspace_id, location_id), 
	FOREIGN KEY(workspace_id) REFERENCES saas_workspaces (id)
);
CREATE TABLE square_refunds (
	id VARCHAR(36) NOT NULL, 
	workspace_id VARCHAR(36) NOT NULL, 
	source_refund_id VARCHAR(160) NOT NULL, 
	order_id VARCHAR(160), 
	location_id VARCHAR(160) NOT NULL, 
	created_at VARCHAR(55) NOT NULL, 
	local_date VARCHAR(10) NOT NULL, 
	amount_minor INTEGER NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_square_refund_owner UNIQUE (workspace_id, source_refund_id), 
	FOREIGN KEY(workspace_id) REFERENCES saas_workspaces (id)
);
CREATE TABLE square_sandbox_connections (
	id VARCHAR(36) NOT NULL, 
	workspace_id VARCHAR(36) NOT NULL, 
	merchant_id VARCHAR(160) NOT NULL, 
	credential_mode VARCHAR(30) NOT NULL, 
	token_ciphertext TEXT, 
	refresh_ciphertext TEXT, 
	token_expires_at VARCHAR(48), 
	connected_at VARCHAR(48) NOT NULL, 
	last_sync_at VARCHAR(48), 
	last_error VARCHAR(220), 
	status VARCHAR(20) DEFAULT 'active' NOT NULL, 
	environment VARCHAR(12) DEFAULT 'sandbox' NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES saas_workspaces (id), 
	UNIQUE (merchant_id)
);
CREATE TABLE square_sandbox_oauth_states (
	state_hash VARCHAR(64) NOT NULL, 
	workspace_id VARCHAR(36) NOT NULL, 
	expires_at INTEGER NOT NULL, 
	PRIMARY KEY (state_hash), 
	FOREIGN KEY(workspace_id) REFERENCES saas_workspaces (id)
);
CREATE TABLE square_sandbox_orders (
	id VARCHAR(36) NOT NULL, 
	workspace_id VARCHAR(36) NOT NULL, 
	source_order_id VARCHAR(160) NOT NULL, 
	location_id VARCHAR(160) NOT NULL, 
	created_at VARCHAR(55) NOT NULL, 
	updated_at VARCHAR(55) NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	customer_id VARCHAR(140), 
	net_sales_minor INTEGER NOT NULL, 
	discount_minor INTEGER NOT NULL, 
	tax_minor INTEGER NOT NULL, 
	tip_minor INTEGER NOT NULL, 
	service_charge_minor INTEGER DEFAULT '0' NOT NULL, 
	local_date VARCHAR(10), 
	currency VARCHAR(4) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_sandbox_order_owner UNIQUE (workspace_id, source_order_id), 
	FOREIGN KEY(workspace_id) REFERENCES saas_workspaces (id)
);
CREATE TABLE square_sandbox_sync_runs (
	id VARCHAR(36) NOT NULL, 
	workspace_id VARCHAR(36) NOT NULL, 
	started_at VARCHAR(48) NOT NULL, 
	completed_at VARCHAR(48), 
	status VARCHAR(18) NOT NULL, 
	scanned INTEGER NOT NULL, 
	inserted INTEGER NOT NULL, 
	updated INTEGER NOT NULL, 
	skipped INTEGER NOT NULL, 
	message VARCHAR(200) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES saas_workspaces (id)
);
CREATE TABLE square_sync_jobs (
	id VARCHAR(36) NOT NULL, 
	workspace_id VARCHAR(36) NOT NULL, 
	kind VARCHAR(20) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	attempts INTEGER NOT NULL, 
	run_after INTEGER NOT NULL, 
	locked_until INTEGER NOT NULL, 
	progress TEXT NOT NULL, 
	last_error VARCHAR(220) NOT NULL, 
	created_at VARCHAR(48) NOT NULL, 
	updated_at VARCHAR(48) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES saas_workspaces (id)
);
CREATE TABLE tablesignal_decision_plans (
	id VARCHAR(36) NOT NULL, 
	workspace_id VARCHAR(36) NOT NULL, 
	title VARCHAR(140) NOT NULL, 
	objective VARCHAR(40) NOT NULL, 
	offer_type VARCHAR(30) NOT NULL, 
	offer_value INTEGER NOT NULL, 
	target_redemptions INTEGER NOT NULL, 
	reference_basket_minor INTEGER NOT NULL, 
	assumed_margin_percent INTEGER NOT NULL, 
	discount_budget_minor INTEGER NOT NULL, 
	modeled_contribution_minor INTEGER NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	notes TEXT NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	updated_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES saas_workspaces (id)
);
CREATE TABLE tablesignal_onboarding_progress (
	workspace_id VARCHAR(36) NOT NULL, 
	stage INTEGER NOT NULL, 
	plan_choice VARCHAR(20) NOT NULL, 
	updated_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (workspace_id), 
	FOREIGN KEY(workspace_id) REFERENCES saas_workspaces (id)
);
CREATE TABLE workspace_invites (
	id VARCHAR(36) NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	workspace_id VARCHAR(36) NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	email VARCHAR(254) NOT NULL, 
	created_by VARCHAR(160) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	expires_at INTEGER NOT NULL, 
	accepted_at VARCHAR(40), 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES saas_workspaces (id)
);
CREATE TABLE workspace_members (
	id VARCHAR(36) NOT NULL, 
	workspace_id VARCHAR(36) NOT NULL, 
	subject VARCHAR(160) NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	email VARCHAR(254) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES saas_workspaces (id)
);
CREATE INDEX ix_canonical_orders_workspace_id ON canonical_orders (workspace_id);
CREATE INDEX ix_import_runs_workspace_id ON import_runs (workspace_id);
CREATE INDEX ix_campaign_redemptions_workspace_id ON campaign_redemptions (workspace_id);
CREATE INDEX ix_campaign_redemptions_campaign_id ON campaign_redemptions (campaign_id);
CREATE INDEX ix_campaign_import_runs_workspace_id ON campaign_import_runs (workspace_id);
CREATE UNIQUE INDEX ix_local_users_email ON local_users (email);
CREATE UNIQUE INDEX ix_saas_workspaces_owner_sub ON saas_workspaces (owner_sub);
CREATE INDEX ix_local_sessions_user_id ON local_sessions (user_id);
CREATE INDEX ix_local_sessions_expires_at ON local_sessions (expires_at);
CREATE UNIQUE INDEX ix_workspace_members_subject ON workspace_members (subject);
CREATE INDEX ix_workspace_members_workspace_id ON workspace_members (workspace_id);
CREATE UNIQUE INDEX ix_workspace_invites_token_hash ON workspace_invites (token_hash);
CREATE INDEX ix_workspace_invites_workspace_id ON workspace_invites (workspace_id);
CREATE INDEX ix_saas_workspace_demo_orders_workspace_id ON saas_workspace_demo_orders (workspace_id);
CREATE UNIQUE INDEX ix_square_sandbox_connections_workspace_id ON square_sandbox_connections (workspace_id);
CREATE INDEX ix_square_sandbox_oauth_states_workspace_id ON square_sandbox_oauth_states (workspace_id);
CREATE INDEX ix_square_sandbox_orders_workspace_id ON square_sandbox_orders (workspace_id);
CREATE INDEX ix_square_sandbox_orders_local_date ON square_sandbox_orders (local_date);
CREATE INDEX ix_square_sandbox_sync_runs_workspace_id ON square_sandbox_sync_runs (workspace_id);
CREATE INDEX ix_assisted_setup_requests_workspace_id ON assisted_setup_requests (workspace_id);
CREATE INDEX ix_tablesignal_decision_plans_workspace_id ON tablesignal_decision_plans (workspace_id);
CREATE INDEX ix_square_refunds_local_date ON square_refunds (local_date);
CREATE INDEX ix_square_refunds_workspace_id ON square_refunds (workspace_id);
CREATE INDEX ix_square_sync_jobs_status ON square_sync_jobs (status);
CREATE INDEX ix_square_sync_jobs_workspace_id ON square_sync_jobs (workspace_id);
CREATE INDEX ix_square_sync_jobs_run_after ON square_sync_jobs (run_after);
