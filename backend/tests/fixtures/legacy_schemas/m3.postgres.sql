-- Schema created by create_all() at commit 7537614 (scripts/make-legacy-schema-fixtures.sh)
--
-- PostgreSQL database dump
--


-- Dumped from database version 16.16 (Debian 16.16-1.pgdg13+1)
-- Dumped by pg_dump version 16.16 (Debian 16.16-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: assisted_setup_requests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assisted_setup_requests (
    id character varying(36) NOT NULL,
    workspace_id character varying(36) NOT NULL,
    provider character varying(30) NOT NULL,
    note character varying(300) NOT NULL,
    status character varying(30) NOT NULL,
    created_at character varying(48) NOT NULL
);


--
-- Name: campaign_import_runs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.campaign_import_runs (
    id integer NOT NULL,
    workspace_id character varying(36) DEFAULT 'public-demo'::character varying NOT NULL,
    processed_at character varying(40) NOT NULL,
    campaigns_inserted integer NOT NULL,
    redemptions_inserted integer NOT NULL,
    duplicates integer NOT NULL,
    rejected integer NOT NULL,
    issues_json text NOT NULL
);


--
-- Name: campaign_import_runs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.campaign_import_runs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: campaign_import_runs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.campaign_import_runs_id_seq OWNED BY public.campaign_import_runs.id;


--
-- Name: campaign_redemptions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.campaign_redemptions (
    id integer NOT NULL,
    workspace_id character varying(36) DEFAULT 'public-demo'::character varying NOT NULL,
    redemption_id character varying(120) NOT NULL,
    campaign_id character varying(80) NOT NULL,
    provider character varying(20) NOT NULL,
    source_order_id character varying(120) NOT NULL,
    redeemed_at character varying(40) NOT NULL,
    discount_minor integer NOT NULL
);


--
-- Name: campaign_redemptions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.campaign_redemptions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: campaign_redemptions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.campaign_redemptions_id_seq OWNED BY public.campaign_redemptions.id;


--
-- Name: campaigns; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.campaigns (
    workspace_id character varying(36) DEFAULT 'public-demo'::character varying NOT NULL,
    campaign_id character varying(80) NOT NULL,
    code character varying(80) NOT NULL,
    name character varying(160) NOT NULL,
    offer_type character varying(30) NOT NULL,
    start_date character varying(10) NOT NULL,
    end_date character varying(10) NOT NULL,
    variable_cost_minor integer NOT NULL,
    fixed_cost_minor integer NOT NULL,
    description text NOT NULL
);


--
-- Name: canonical_orders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.canonical_orders (
    id integer NOT NULL,
    workspace_id character varying(36) DEFAULT 'public-demo'::character varying NOT NULL,
    provider character varying(20) NOT NULL,
    source_order_id character varying(120) NOT NULL,
    location_id character varying(120) NOT NULL,
    created_at character varying(80) NOT NULL,
    customer_id character varying(120),
    net_sales_minor integer NOT NULL,
    discount_minor integer NOT NULL,
    refund_minor integer NOT NULL,
    payload_json text NOT NULL
);


--
-- Name: canonical_orders_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.canonical_orders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: canonical_orders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.canonical_orders_id_seq OWNED BY public.canonical_orders.id;


--
-- Name: import_runs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.import_runs (
    id integer NOT NULL,
    workspace_id character varying(36) DEFAULT 'public-demo'::character varying NOT NULL,
    provider character varying(20) NOT NULL,
    processed_at character varying(40) NOT NULL,
    inserted integer NOT NULL,
    duplicates integer NOT NULL,
    status character varying(30) NOT NULL
);


--
-- Name: import_runs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.import_runs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: import_runs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.import_runs_id_seq OWNED BY public.import_runs.id;


--
-- Name: local_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.local_sessions (
    token_hash character varying(64) NOT NULL,
    user_id character varying(36) NOT NULL,
    csrf_token character varying(100) NOT NULL,
    created_at integer NOT NULL,
    expires_at integer NOT NULL
);


--
-- Name: local_users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.local_users (
    id character varying(36) NOT NULL,
    email character varying(254) NOT NULL,
    password_hash character varying(320) NOT NULL,
    created_at character varying(40) NOT NULL
);


--
-- Name: saas_billing_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.saas_billing_events (
    stripe_event_id character varying(160) NOT NULL,
    processed_at character varying(40) NOT NULL
);


--
-- Name: saas_workspace_demo_orders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.saas_workspace_demo_orders (
    id integer NOT NULL,
    workspace_id character varying(36) NOT NULL,
    provider character varying(20) NOT NULL,
    source_order_id character varying(140) NOT NULL,
    location_id character varying(120) NOT NULL,
    created_at character varying(80) NOT NULL,
    status character varying(35) NOT NULL,
    customer_id character varying(140),
    net_sales_minor integer NOT NULL,
    discount_minor integer NOT NULL,
    campaign_code character varying(100),
    campaign_discount_minor integer NOT NULL
);


--
-- Name: saas_workspace_demo_orders_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.saas_workspace_demo_orders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: saas_workspace_demo_orders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.saas_workspace_demo_orders_id_seq OWNED BY public.saas_workspace_demo_orders.id;


--
-- Name: saas_workspaces; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.saas_workspaces (
    id character varying(36) NOT NULL,
    owner_sub character varying(160) NOT NULL,
    name character varying(120) NOT NULL,
    restaurant_type character varying(35) NOT NULL,
    goal character varying(40) NOT NULL,
    subscription_plan character varying(20) NOT NULL,
    subscription_status character varying(35) NOT NULL,
    stripe_customer_id character varying(120),
    stripe_subscription_id character varying(120),
    created_at character varying(40) NOT NULL
);


--
-- Name: sandbox_monitored_locations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sandbox_monitored_locations (
    workspace_id character varying(36) NOT NULL,
    location_id character varying(160) NOT NULL,
    merchant_id character varying(160) NOT NULL,
    name character varying(160) NOT NULL,
    selected_at character varying(48) NOT NULL
);


--
-- Name: square_location_state; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.square_location_state (
    workspace_id character varying(36) NOT NULL,
    location_id character varying(160) NOT NULL,
    name character varying(160) NOT NULL,
    timezone character varying(64) NOT NULL,
    backfill_start character varying(32) NOT NULL,
    synced_through character varying(32),
    backfill_complete boolean NOT NULL,
    updated_at character varying(48) NOT NULL
);


--
-- Name: square_refunds; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.square_refunds (
    id character varying(36) NOT NULL,
    workspace_id character varying(36) NOT NULL,
    source_refund_id character varying(160) NOT NULL,
    order_id character varying(160),
    location_id character varying(160) NOT NULL,
    created_at character varying(55) NOT NULL,
    local_date character varying(10) NOT NULL,
    amount_minor integer NOT NULL,
    status character varying(30) NOT NULL
);


--
-- Name: square_sandbox_connections; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.square_sandbox_connections (
    id character varying(36) NOT NULL,
    workspace_id character varying(36) NOT NULL,
    merchant_id character varying(160) NOT NULL,
    credential_mode character varying(30) NOT NULL,
    token_ciphertext text,
    refresh_ciphertext text,
    token_expires_at character varying(48),
    connected_at character varying(48) NOT NULL,
    last_sync_at character varying(48),
    last_error character varying(220),
    status character varying(20) DEFAULT 'active'::character varying NOT NULL,
    environment character varying(12) DEFAULT 'sandbox'::character varying NOT NULL
);


--
-- Name: square_sandbox_oauth_states; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.square_sandbox_oauth_states (
    state_hash character varying(64) NOT NULL,
    workspace_id character varying(36) NOT NULL,
    expires_at integer NOT NULL
);


--
-- Name: square_sandbox_orders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.square_sandbox_orders (
    id character varying(36) NOT NULL,
    workspace_id character varying(36) NOT NULL,
    source_order_id character varying(160) NOT NULL,
    location_id character varying(160) NOT NULL,
    created_at character varying(55) NOT NULL,
    updated_at character varying(55) NOT NULL,
    status character varying(40) NOT NULL,
    customer_id character varying(140),
    net_sales_minor integer NOT NULL,
    discount_minor integer NOT NULL,
    tax_minor integer NOT NULL,
    tip_minor integer NOT NULL,
    service_charge_minor integer DEFAULT 0 NOT NULL,
    local_date character varying(10),
    currency character varying(4) NOT NULL
);


--
-- Name: square_sandbox_sync_runs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.square_sandbox_sync_runs (
    id character varying(36) NOT NULL,
    workspace_id character varying(36) NOT NULL,
    started_at character varying(48) NOT NULL,
    completed_at character varying(48),
    status character varying(18) NOT NULL,
    scanned integer NOT NULL,
    inserted integer NOT NULL,
    updated integer NOT NULL,
    skipped integer NOT NULL,
    message character varying(200) NOT NULL
);


--
-- Name: square_sync_jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.square_sync_jobs (
    id character varying(36) NOT NULL,
    workspace_id character varying(36) NOT NULL,
    kind character varying(20) NOT NULL,
    status character varying(20) NOT NULL,
    attempts integer NOT NULL,
    run_after integer NOT NULL,
    locked_until integer NOT NULL,
    progress text NOT NULL,
    last_error character varying(220) NOT NULL,
    created_at character varying(48) NOT NULL,
    updated_at character varying(48) NOT NULL
);


--
-- Name: tablesignal_decision_plans; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tablesignal_decision_plans (
    id character varying(36) NOT NULL,
    workspace_id character varying(36) NOT NULL,
    title character varying(140) NOT NULL,
    objective character varying(40) NOT NULL,
    offer_type character varying(30) NOT NULL,
    offer_value integer NOT NULL,
    target_redemptions integer NOT NULL,
    reference_basket_minor integer NOT NULL,
    assumed_margin_percent integer NOT NULL,
    discount_budget_minor integer NOT NULL,
    modeled_contribution_minor integer NOT NULL,
    status character varying(20) NOT NULL,
    notes text NOT NULL,
    created_at character varying(40) NOT NULL,
    updated_at character varying(40) NOT NULL
);


--
-- Name: tablesignal_onboarding_progress; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tablesignal_onboarding_progress (
    workspace_id character varying(36) NOT NULL,
    stage integer NOT NULL,
    plan_choice character varying(20) NOT NULL,
    updated_at character varying(40) NOT NULL
);


--
-- Name: workspace_invites; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workspace_invites (
    id character varying(36) NOT NULL,
    token_hash character varying(64) NOT NULL,
    workspace_id character varying(36) NOT NULL,
    role character varying(20) NOT NULL,
    email character varying(254) NOT NULL,
    created_by character varying(160) NOT NULL,
    created_at character varying(40) NOT NULL,
    expires_at integer NOT NULL,
    accepted_at character varying(40)
);


--
-- Name: workspace_members; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workspace_members (
    id character varying(36) NOT NULL,
    workspace_id character varying(36) NOT NULL,
    subject character varying(160) NOT NULL,
    role character varying(20) NOT NULL,
    email character varying(254) NOT NULL,
    created_at character varying(40) NOT NULL
);


--
-- Name: campaign_import_runs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_import_runs ALTER COLUMN id SET DEFAULT nextval('public.campaign_import_runs_id_seq'::regclass);


--
-- Name: campaign_redemptions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_redemptions ALTER COLUMN id SET DEFAULT nextval('public.campaign_redemptions_id_seq'::regclass);


--
-- Name: canonical_orders id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.canonical_orders ALTER COLUMN id SET DEFAULT nextval('public.canonical_orders_id_seq'::regclass);


--
-- Name: import_runs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.import_runs ALTER COLUMN id SET DEFAULT nextval('public.import_runs_id_seq'::regclass);


--
-- Name: saas_workspace_demo_orders id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.saas_workspace_demo_orders ALTER COLUMN id SET DEFAULT nextval('public.saas_workspace_demo_orders_id_seq'::regclass);


--
-- Name: assisted_setup_requests assisted_setup_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assisted_setup_requests
    ADD CONSTRAINT assisted_setup_requests_pkey PRIMARY KEY (id);


--
-- Name: campaign_import_runs campaign_import_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_import_runs
    ADD CONSTRAINT campaign_import_runs_pkey PRIMARY KEY (id);


--
-- Name: campaign_redemptions campaign_redemptions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_redemptions
    ADD CONSTRAINT campaign_redemptions_pkey PRIMARY KEY (id);


--
-- Name: campaigns campaigns_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaigns
    ADD CONSTRAINT campaigns_pkey PRIMARY KEY (workspace_id, campaign_id);


--
-- Name: canonical_orders canonical_orders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.canonical_orders
    ADD CONSTRAINT canonical_orders_pkey PRIMARY KEY (id);


--
-- Name: import_runs import_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.import_runs
    ADD CONSTRAINT import_runs_pkey PRIMARY KEY (id);


--
-- Name: local_sessions local_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.local_sessions
    ADD CONSTRAINT local_sessions_pkey PRIMARY KEY (token_hash);


--
-- Name: local_users local_users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.local_users
    ADD CONSTRAINT local_users_pkey PRIMARY KEY (id);


--
-- Name: saas_billing_events saas_billing_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.saas_billing_events
    ADD CONSTRAINT saas_billing_events_pkey PRIMARY KEY (stripe_event_id);


--
-- Name: saas_workspace_demo_orders saas_workspace_demo_orders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.saas_workspace_demo_orders
    ADD CONSTRAINT saas_workspace_demo_orders_pkey PRIMARY KEY (id);


--
-- Name: saas_workspaces saas_workspaces_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.saas_workspaces
    ADD CONSTRAINT saas_workspaces_pkey PRIMARY KEY (id);


--
-- Name: saas_workspaces saas_workspaces_stripe_customer_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.saas_workspaces
    ADD CONSTRAINT saas_workspaces_stripe_customer_id_key UNIQUE (stripe_customer_id);


--
-- Name: saas_workspaces saas_workspaces_stripe_subscription_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.saas_workspaces
    ADD CONSTRAINT saas_workspaces_stripe_subscription_id_key UNIQUE (stripe_subscription_id);


--
-- Name: sandbox_monitored_locations sandbox_monitored_locations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sandbox_monitored_locations
    ADD CONSTRAINT sandbox_monitored_locations_pkey PRIMARY KEY (workspace_id, location_id);


--
-- Name: square_location_state square_location_state_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.square_location_state
    ADD CONSTRAINT square_location_state_pkey PRIMARY KEY (workspace_id, location_id);


--
-- Name: square_refunds square_refunds_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.square_refunds
    ADD CONSTRAINT square_refunds_pkey PRIMARY KEY (id);


--
-- Name: square_sandbox_connections square_sandbox_connections_merchant_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.square_sandbox_connections
    ADD CONSTRAINT square_sandbox_connections_merchant_id_key UNIQUE (merchant_id);


--
-- Name: square_sandbox_connections square_sandbox_connections_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.square_sandbox_connections
    ADD CONSTRAINT square_sandbox_connections_pkey PRIMARY KEY (id);


--
-- Name: square_sandbox_oauth_states square_sandbox_oauth_states_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.square_sandbox_oauth_states
    ADD CONSTRAINT square_sandbox_oauth_states_pkey PRIMARY KEY (state_hash);


--
-- Name: square_sandbox_orders square_sandbox_orders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.square_sandbox_orders
    ADD CONSTRAINT square_sandbox_orders_pkey PRIMARY KEY (id);


--
-- Name: square_sandbox_sync_runs square_sandbox_sync_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.square_sandbox_sync_runs
    ADD CONSTRAINT square_sandbox_sync_runs_pkey PRIMARY KEY (id);


--
-- Name: square_sync_jobs square_sync_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.square_sync_jobs
    ADD CONSTRAINT square_sync_jobs_pkey PRIMARY KEY (id);


--
-- Name: tablesignal_decision_plans tablesignal_decision_plans_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tablesignal_decision_plans
    ADD CONSTRAINT tablesignal_decision_plans_pkey PRIMARY KEY (id);


--
-- Name: tablesignal_onboarding_progress tablesignal_onboarding_progress_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tablesignal_onboarding_progress
    ADD CONSTRAINT tablesignal_onboarding_progress_pkey PRIMARY KEY (workspace_id);


--
-- Name: saas_workspace_demo_orders uq_saas_demo_order; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.saas_workspace_demo_orders
    ADD CONSTRAINT uq_saas_demo_order UNIQUE (workspace_id, provider, source_order_id);


--
-- Name: square_sandbox_orders uq_sandbox_order_owner; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.square_sandbox_orders
    ADD CONSTRAINT uq_sandbox_order_owner UNIQUE (workspace_id, source_order_id);


--
-- Name: square_refunds uq_square_refund_owner; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.square_refunds
    ADD CONSTRAINT uq_square_refund_owner UNIQUE (workspace_id, source_refund_id);


--
-- Name: campaign_redemptions uq_workspace_one_campaign_per_order; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_redemptions
    ADD CONSTRAINT uq_workspace_one_campaign_per_order UNIQUE (workspace_id, provider, source_order_id);


--
-- Name: canonical_orders uq_workspace_provider_order; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.canonical_orders
    ADD CONSTRAINT uq_workspace_provider_order UNIQUE (workspace_id, provider, source_order_id);


--
-- Name: campaign_redemptions uq_workspace_redemption; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign_redemptions
    ADD CONSTRAINT uq_workspace_redemption UNIQUE (workspace_id, redemption_id);


--
-- Name: workspace_invites workspace_invites_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspace_invites
    ADD CONSTRAINT workspace_invites_pkey PRIMARY KEY (id);


--
-- Name: workspace_members workspace_members_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspace_members
    ADD CONSTRAINT workspace_members_pkey PRIMARY KEY (id);


--
-- Name: ix_assisted_setup_requests_workspace_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_assisted_setup_requests_workspace_id ON public.assisted_setup_requests USING btree (workspace_id);


--
-- Name: ix_campaign_import_runs_workspace_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_campaign_import_runs_workspace_id ON public.campaign_import_runs USING btree (workspace_id);


--
-- Name: ix_campaign_redemptions_campaign_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_campaign_redemptions_campaign_id ON public.campaign_redemptions USING btree (campaign_id);


--
-- Name: ix_campaign_redemptions_workspace_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_campaign_redemptions_workspace_id ON public.campaign_redemptions USING btree (workspace_id);


--
-- Name: ix_canonical_orders_workspace_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_canonical_orders_workspace_id ON public.canonical_orders USING btree (workspace_id);


--
-- Name: ix_import_runs_workspace_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_import_runs_workspace_id ON public.import_runs USING btree (workspace_id);


--
-- Name: ix_local_sessions_expires_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_local_sessions_expires_at ON public.local_sessions USING btree (expires_at);


--
-- Name: ix_local_sessions_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_local_sessions_user_id ON public.local_sessions USING btree (user_id);


--
-- Name: ix_local_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_local_users_email ON public.local_users USING btree (email);


--
-- Name: ix_saas_workspace_demo_orders_workspace_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_saas_workspace_demo_orders_workspace_id ON public.saas_workspace_demo_orders USING btree (workspace_id);


--
-- Name: ix_saas_workspaces_owner_sub; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_saas_workspaces_owner_sub ON public.saas_workspaces USING btree (owner_sub);


--
-- Name: ix_square_refunds_local_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_square_refunds_local_date ON public.square_refunds USING btree (local_date);


--
-- Name: ix_square_refunds_workspace_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_square_refunds_workspace_id ON public.square_refunds USING btree (workspace_id);


--
-- Name: ix_square_sandbox_connections_workspace_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_square_sandbox_connections_workspace_id ON public.square_sandbox_connections USING btree (workspace_id);


--
-- Name: ix_square_sandbox_oauth_states_workspace_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_square_sandbox_oauth_states_workspace_id ON public.square_sandbox_oauth_states USING btree (workspace_id);


--
-- Name: ix_square_sandbox_orders_local_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_square_sandbox_orders_local_date ON public.square_sandbox_orders USING btree (local_date);


--
-- Name: ix_square_sandbox_orders_workspace_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_square_sandbox_orders_workspace_id ON public.square_sandbox_orders USING btree (workspace_id);


--
-- Name: ix_square_sandbox_sync_runs_workspace_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_square_sandbox_sync_runs_workspace_id ON public.square_sandbox_sync_runs USING btree (workspace_id);


--
-- Name: ix_square_sync_jobs_run_after; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_square_sync_jobs_run_after ON public.square_sync_jobs USING btree (run_after);


--
-- Name: ix_square_sync_jobs_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_square_sync_jobs_status ON public.square_sync_jobs USING btree (status);


--
-- Name: ix_square_sync_jobs_workspace_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_square_sync_jobs_workspace_id ON public.square_sync_jobs USING btree (workspace_id);


--
-- Name: ix_tablesignal_decision_plans_workspace_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tablesignal_decision_plans_workspace_id ON public.tablesignal_decision_plans USING btree (workspace_id);


--
-- Name: ix_workspace_invites_token_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_workspace_invites_token_hash ON public.workspace_invites USING btree (token_hash);


--
-- Name: ix_workspace_invites_workspace_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_workspace_invites_workspace_id ON public.workspace_invites USING btree (workspace_id);


--
-- Name: ix_workspace_members_subject; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_workspace_members_subject ON public.workspace_members USING btree (subject);


--
-- Name: ix_workspace_members_workspace_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_workspace_members_workspace_id ON public.workspace_members USING btree (workspace_id);


--
-- Name: assisted_setup_requests assisted_setup_requests_workspace_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assisted_setup_requests
    ADD CONSTRAINT assisted_setup_requests_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.saas_workspaces(id);


--
-- Name: local_sessions local_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.local_sessions
    ADD CONSTRAINT local_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.local_users(id);


--
-- Name: saas_workspace_demo_orders saas_workspace_demo_orders_workspace_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.saas_workspace_demo_orders
    ADD CONSTRAINT saas_workspace_demo_orders_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.saas_workspaces(id);


--
-- Name: sandbox_monitored_locations sandbox_monitored_locations_workspace_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sandbox_monitored_locations
    ADD CONSTRAINT sandbox_monitored_locations_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.saas_workspaces(id);


--
-- Name: square_location_state square_location_state_workspace_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.square_location_state
    ADD CONSTRAINT square_location_state_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.saas_workspaces(id);


--
-- Name: square_refunds square_refunds_workspace_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.square_refunds
    ADD CONSTRAINT square_refunds_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.saas_workspaces(id);


--
-- Name: square_sandbox_connections square_sandbox_connections_workspace_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.square_sandbox_connections
    ADD CONSTRAINT square_sandbox_connections_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.saas_workspaces(id);


--
-- Name: square_sandbox_oauth_states square_sandbox_oauth_states_workspace_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.square_sandbox_oauth_states
    ADD CONSTRAINT square_sandbox_oauth_states_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.saas_workspaces(id);


--
-- Name: square_sandbox_orders square_sandbox_orders_workspace_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.square_sandbox_orders
    ADD CONSTRAINT square_sandbox_orders_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.saas_workspaces(id);


--
-- Name: square_sandbox_sync_runs square_sandbox_sync_runs_workspace_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.square_sandbox_sync_runs
    ADD CONSTRAINT square_sandbox_sync_runs_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.saas_workspaces(id);


--
-- Name: square_sync_jobs square_sync_jobs_workspace_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.square_sync_jobs
    ADD CONSTRAINT square_sync_jobs_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.saas_workspaces(id);


--
-- Name: tablesignal_decision_plans tablesignal_decision_plans_workspace_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tablesignal_decision_plans
    ADD CONSTRAINT tablesignal_decision_plans_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.saas_workspaces(id);


--
-- Name: tablesignal_onboarding_progress tablesignal_onboarding_progress_workspace_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tablesignal_onboarding_progress
    ADD CONSTRAINT tablesignal_onboarding_progress_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.saas_workspaces(id);


--
-- Name: workspace_invites workspace_invites_workspace_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspace_invites
    ADD CONSTRAINT workspace_invites_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.saas_workspaces(id);


--
-- Name: workspace_members workspace_members_workspace_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspace_members
    ADD CONSTRAINT workspace_members_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.saas_workspaces(id);


--
-- PostgreSQL database dump complete
--


