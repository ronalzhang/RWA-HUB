--
-- PostgreSQL database dump
--

-- Dumped from database version 14.15 (Homebrew)
-- Dumped by pg_dump version 14.15 (Homebrew)

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

ALTER TABLE IF EXISTS ONLY public.user_referrals DROP CONSTRAINT IF EXISTS user_referrals_asset_id_fkey;
ALTER TABLE IF EXISTS ONLY public.trades DROP CONSTRAINT IF EXISTS trades_asset_id_fkey;
ALTER TABLE IF EXISTS ONLY public.platform_incomes DROP CONSTRAINT IF EXISTS platform_incomes_asset_id_fkey;
ALTER TABLE IF EXISTS ONLY public.onchain_history DROP CONSTRAINT IF EXISTS onchain_history_trade_id_fkey;
ALTER TABLE IF EXISTS ONLY public.onchain_history DROP CONSTRAINT IF EXISTS onchain_history_asset_id_fkey;
ALTER TABLE IF EXISTS ONLY public.holdings DROP CONSTRAINT IF EXISTS holdings_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.holdings DROP CONSTRAINT IF EXISTS holdings_asset_id_fkey;
ALTER TABLE IF EXISTS ONLY public.dividends DROP CONSTRAINT IF EXISTS dividends_asset_id_fkey;
ALTER TABLE IF EXISTS ONLY public.dividend_records DROP CONSTRAINT IF EXISTS dividend_records_asset_id_fkey;
ALTER TABLE IF EXISTS ONLY public.dividend_distributions DROP CONSTRAINT IF EXISTS dividend_distributions_dividend_record_id_fkey;
ALTER TABLE IF EXISTS ONLY public.commission_records DROP CONSTRAINT IF EXISTS commission_records_transaction_id_fkey;
ALTER TABLE IF EXISTS ONLY public.commission_records DROP CONSTRAINT IF EXISTS commission_records_asset_id_fkey;
ALTER TABLE IF EXISTS ONLY public.asset_status_history DROP CONSTRAINT IF EXISTS asset_status_history_asset_id_fkey;
DROP TRIGGER IF EXISTS assets_sequence_check ON public.assets;
DROP INDEX IF EXISTS public.ix_transactions_to_address;
DROP INDEX IF EXISTS public.ix_transactions_from_address;
DROP INDEX IF EXISTS public.ix_short_links_code;
DROP INDEX IF EXISTS public.ix_ip_visits_timestamp;
DROP INDEX IF EXISTS public.ix_ip_visits_ip_address;
DROP INDEX IF EXISTS public.ix_commission_withdrawals_user_address;
DROP INDEX IF EXISTS public.ix_assets_status;
DROP INDEX IF EXISTS public.ix_assets_name;
DROP INDEX IF EXISTS public.ix_assets_location;
DROP INDEX IF EXISTS public.ix_assets_created_at;
DROP INDEX IF EXISTS public.ix_assets_asset_type;
DROP INDEX IF EXISTS public.idx_user_holdings;
DROP INDEX IF EXISTS public.idx_timestamp_desc;
DROP INDEX IF EXISTS public.idx_ip_timestamp;
DROP INDEX IF EXISTS public.idx_asset_holders;
DROP INDEX IF EXISTS public.idx_active_holdings;
ALTER TABLE IF EXISTS ONLY public.withdrawal_requests DROP CONSTRAINT IF EXISTS withdrawal_requests_pkey;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_username_key;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_solana_address_key;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_pkey;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_eth_address_key;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_email_key;
ALTER TABLE IF EXISTS ONLY public.user_referrals DROP CONSTRAINT IF EXISTS user_referrals_user_address_key;
ALTER TABLE IF EXISTS ONLY public.user_referrals DROP CONSTRAINT IF EXISTS user_referrals_pkey;
ALTER TABLE IF EXISTS ONLY public.user_commission_balance DROP CONSTRAINT IF EXISTS user_commission_balance_user_address_key;
ALTER TABLE IF EXISTS ONLY public.user_commission_balance DROP CONSTRAINT IF EXISTS user_commission_balance_pkey;
ALTER TABLE IF EXISTS ONLY public.holdings DROP CONSTRAINT IF EXISTS uix_user_asset;
ALTER TABLE IF EXISTS ONLY public.transactions DROP CONSTRAINT IF EXISTS transactions_signature_key;
ALTER TABLE IF EXISTS ONLY public.transactions DROP CONSTRAINT IF EXISTS transactions_pkey;
ALTER TABLE IF EXISTS ONLY public.trades DROP CONSTRAINT IF EXISTS trades_pkey;
ALTER TABLE IF EXISTS ONLY public.system_configs DROP CONSTRAINT IF EXISTS system_configs_pkey;
ALTER TABLE IF EXISTS ONLY public.system_configs DROP CONSTRAINT IF EXISTS system_configs_config_key_key;
ALTER TABLE IF EXISTS ONLY public.short_links DROP CONSTRAINT IF EXISTS short_links_pkey;
ALTER TABLE IF EXISTS ONLY public.share_messages DROP CONSTRAINT IF EXISTS share_messages_pkey;
ALTER TABLE IF EXISTS ONLY public.platform_incomes DROP CONSTRAINT IF EXISTS platform_incomes_pkey;
ALTER TABLE IF EXISTS ONLY public.onchain_history DROP CONSTRAINT IF EXISTS onchain_history_pkey;
ALTER TABLE IF EXISTS ONLY public.ip_visits DROP CONSTRAINT IF EXISTS ip_visits_pkey;
ALTER TABLE IF EXISTS ONLY public.holdings DROP CONSTRAINT IF EXISTS holdings_pkey;
ALTER TABLE IF EXISTS ONLY public.dividends DROP CONSTRAINT IF EXISTS dividends_pkey;
ALTER TABLE IF EXISTS ONLY public.dividend_records DROP CONSTRAINT IF EXISTS dividend_records_pkey;
ALTER TABLE IF EXISTS ONLY public.dividend_distributions DROP CONSTRAINT IF EXISTS dividend_distributions_pkey;
ALTER TABLE IF EXISTS ONLY public.distribution_settings DROP CONSTRAINT IF EXISTS distribution_settings_pkey;
ALTER TABLE IF EXISTS ONLY public.distribution_levels DROP CONSTRAINT IF EXISTS distribution_levels_pkey;
ALTER TABLE IF EXISTS ONLY public.distribution_levels DROP CONSTRAINT IF EXISTS distribution_levels_level_key;
ALTER TABLE IF EXISTS ONLY public.dashboard_stats DROP CONSTRAINT IF EXISTS dashboard_stats_pkey;
ALTER TABLE IF EXISTS ONLY public.commissions DROP CONSTRAINT IF EXISTS commissions_pkey;
ALTER TABLE IF EXISTS ONLY public.commission_withdrawals DROP CONSTRAINT IF EXISTS commission_withdrawals_pkey;
ALTER TABLE IF EXISTS ONLY public.commission_settings DROP CONSTRAINT IF EXISTS commission_settings_pkey;
ALTER TABLE IF EXISTS ONLY public.commission_records DROP CONSTRAINT IF EXISTS commission_records_pkey;
ALTER TABLE IF EXISTS ONLY public.commission_config DROP CONSTRAINT IF EXISTS commission_config_pkey;
ALTER TABLE IF EXISTS ONLY public.commission_config DROP CONSTRAINT IF EXISTS commission_config_config_key_key;
ALTER TABLE IF EXISTS ONLY public.assets DROP CONSTRAINT IF EXISTS assets_token_symbol_key;
ALTER TABLE IF EXISTS ONLY public.assets DROP CONSTRAINT IF EXISTS assets_token_address_key;
ALTER TABLE IF EXISTS ONLY public.assets DROP CONSTRAINT IF EXISTS assets_pkey;
ALTER TABLE IF EXISTS ONLY public.asset_status_history DROP CONSTRAINT IF EXISTS asset_status_history_pkey;
ALTER TABLE IF EXISTS ONLY public.alembic_version DROP CONSTRAINT IF EXISTS alembic_version_pkc;
ALTER TABLE IF EXISTS ONLY public.admin_users DROP CONSTRAINT IF EXISTS admin_users_wallet_address_key;
ALTER TABLE IF EXISTS ONLY public.admin_users DROP CONSTRAINT IF EXISTS admin_users_pkey;
ALTER TABLE IF EXISTS ONLY public.admin_operation_logs DROP CONSTRAINT IF EXISTS admin_operation_logs_pkey;
ALTER TABLE IF EXISTS public.withdrawal_requests ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.users ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.user_referrals ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.user_commission_balance ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.transactions ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.trades ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.system_configs ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.short_links ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.share_messages ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.platform_incomes ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.onchain_history ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.ip_visits ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.holdings ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.dividends ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.dividend_records ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.dividend_distributions ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.distribution_settings ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.distribution_levels ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.dashboard_stats ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.commissions ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.commission_withdrawals ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.commission_settings ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.commission_records ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.commission_config ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.assets ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.asset_status_history ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.admin_users ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.admin_operation_logs ALTER COLUMN id DROP DEFAULT;
DROP SEQUENCE IF EXISTS public.withdrawal_requests_id_seq;
DROP TABLE IF EXISTS public.withdrawal_requests;
DROP SEQUENCE IF EXISTS public.users_id_seq;
DROP TABLE IF EXISTS public.users;
DROP SEQUENCE IF EXISTS public.user_referrals_id_seq;
DROP TABLE IF EXISTS public.user_referrals;
DROP SEQUENCE IF EXISTS public.user_commission_balance_id_seq;
DROP TABLE IF EXISTS public.user_commission_balance;
DROP SEQUENCE IF EXISTS public.transactions_id_seq;
DROP TABLE IF EXISTS public.transactions;
DROP SEQUENCE IF EXISTS public.trades_id_seq;
DROP TABLE IF EXISTS public.trades;
DROP SEQUENCE IF EXISTS public.system_configs_id_seq;
DROP TABLE IF EXISTS public.system_configs;
DROP SEQUENCE IF EXISTS public.short_links_id_seq;
DROP TABLE IF EXISTS public.short_links;
DROP SEQUENCE IF EXISTS public.share_messages_id_seq;
DROP TABLE IF EXISTS public.share_messages;
DROP SEQUENCE IF EXISTS public.platform_incomes_id_seq;
DROP TABLE IF EXISTS public.platform_incomes;
DROP SEQUENCE IF EXISTS public.onchain_history_id_seq;
DROP TABLE IF EXISTS public.onchain_history;
DROP SEQUENCE IF EXISTS public.ip_visits_id_seq;
DROP TABLE IF EXISTS public.ip_visits;
DROP SEQUENCE IF EXISTS public.holdings_id_seq;
DROP TABLE IF EXISTS public.holdings;
DROP SEQUENCE IF EXISTS public.dividends_id_seq;
DROP TABLE IF EXISTS public.dividends;
DROP SEQUENCE IF EXISTS public.dividend_records_id_seq;
DROP TABLE IF EXISTS public.dividend_records;
DROP SEQUENCE IF EXISTS public.dividend_distributions_id_seq;
DROP TABLE IF EXISTS public.dividend_distributions;
DROP SEQUENCE IF EXISTS public.distribution_settings_id_seq;
DROP TABLE IF EXISTS public.distribution_settings;
DROP SEQUENCE IF EXISTS public.distribution_levels_id_seq;
DROP TABLE IF EXISTS public.distribution_levels;
DROP SEQUENCE IF EXISTS public.dashboard_stats_id_seq;
DROP TABLE IF EXISTS public.dashboard_stats;
DROP SEQUENCE IF EXISTS public.commissions_id_seq;
DROP TABLE IF EXISTS public.commissions;
DROP SEQUENCE IF EXISTS public.commission_withdrawals_id_seq;
DROP TABLE IF EXISTS public.commission_withdrawals;
DROP SEQUENCE IF EXISTS public.commission_settings_id_seq;
DROP TABLE IF EXISTS public.commission_settings;
DROP SEQUENCE IF EXISTS public.commission_records_id_seq;
DROP TABLE IF EXISTS public.commission_records;
DROP SEQUENCE IF EXISTS public.commission_config_id_seq;
DROP TABLE IF EXISTS public.commission_config;
DROP SEQUENCE IF EXISTS public.assets_id_seq;
DROP TABLE IF EXISTS public.assets;
DROP SEQUENCE IF EXISTS public.asset_status_history_id_seq;
DROP TABLE IF EXISTS public.asset_status_history;
DROP TABLE IF EXISTS public.alembic_version;
DROP SEQUENCE IF EXISTS public.admin_users_id_seq;
DROP TABLE IF EXISTS public.admin_users;
DROP SEQUENCE IF EXISTS public.admin_operation_logs_id_seq;
DROP TABLE IF EXISTS public.admin_operation_logs;
DROP FUNCTION IF EXISTS public.check_assets_sequence();
--
-- Name: check_assets_sequence(); Type: FUNCTION; Schema: public; Owner: rwa_hub_user
--

CREATE FUNCTION public.check_assets_sequence() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
            DECLARE
                current_max_id INTEGER;
                seq_value INTEGER;
            BEGIN
                -- 获取当前最大ID
                SELECT COALESCE(MAX(id), 0) INTO current_max_id FROM assets;
                
                -- 获取序列当前值
                SELECT last_value INTO seq_value FROM assets_id_seq;
                
                -- 如果序列值小于最大ID，自动修复
                IF seq_value <= current_max_id THEN
                    PERFORM setval('assets_id_seq', current_max_id + 10, true);
                    RAISE NOTICE '序列已自动修复: 从 % 修复到 %', seq_value, current_max_id + 10;
                END IF;
                
                RETURN NEW;
            END;
            $$;


ALTER FUNCTION public.check_assets_sequence() OWNER TO rwa_hub_user;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: admin_operation_logs; Type: TABLE; Schema: public; Owner: rwa_hub_user
--

CREATE TABLE public.admin_operation_logs (
    id integer NOT NULL,
    admin_address character varying(80) NOT NULL,
    operation_type character varying(50) NOT NULL,
    target_table character varying(50),
    target_id character varying(50),
    operation_details text,
    ip_address character varying(50),
    created_at timestamp without time zone
);


ALTER TABLE public.admin_operation_logs OWNER TO rwa_hub_user;

--
-- Name: admin_operation_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: rwa_hub_user
--

CREATE SEQUENCE public.admin_operation_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.admin_operation_logs_id_seq OWNER TO rwa_hub_user;

--
-- Name: admin_operation_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rwa_hub_user
--

ALTER SEQUENCE public.admin_operation_logs_id_seq OWNED BY public.admin_operation_logs.id;


--
-- Name: admin_users; Type: TABLE; Schema: public; Owner: rwa_hub_user
--

CREATE TABLE public.admin_users (
    id integer NOT NULL,
    wallet_address character varying(100) NOT NULL,
    username character varying(50),
    role character varying(20) NOT NULL,
    permissions text,
    last_login timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.admin_users OWNER TO rwa_hub_user;

--
-- Name: admin_users_id_seq; Type: SEQUENCE; Schema: public; Owner: rwa_hub_user
--

CREATE SEQUENCE public.admin_users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.admin_users_id_seq OWNER TO rwa_hub_user;

--
-- Name: admin_users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rwa_hub_user
--

ALTER SEQUENCE public.admin_users_id_seq OWNED BY public.admin_users.id;


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: rwa_hub_user
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO rwa_hub_user;

--
-- Name: asset_status_history; Type: TABLE; Schema: public; Owner: rwa_hub_user
--

CREATE TABLE public.asset_status_history (
    id integer NOT NULL,
    asset_id integer NOT NULL,
    old_status integer NOT NULL,
    new_status integer NOT NULL,
    change_time timestamp without time zone NOT NULL,
    change_reason character varying(512)
);


ALTER TABLE public.asset_status_history OWNER TO rwa_hub_user;

--
-- Name: asset_status_history_id_seq; Type: SEQUENCE; Schema: public; Owner: rwa_hub_user
--

CREATE SEQUENCE public.asset_status_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.asset_status_history_id_seq OWNER TO rwa_hub_user;

--
-- Name: asset_status_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rwa_hub_user
--

ALTER SEQUENCE public.asset_status_history_id_seq OWNED BY public.asset_status_history.id;


--
-- Name: assets; Type: TABLE; Schema: public; Owner: rwa_hub_user
--

CREATE TABLE public.assets (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    description text,
    asset_type integer NOT NULL,
    location character varying(200) NOT NULL,
    area double precision,
    total_value double precision,
    token_symbol character varying(20) NOT NULL,
    token_price double precision NOT NULL,
    token_supply integer,
    token_address character varying(128),
    annual_revenue double precision NOT NULL,
    images text,
    documents text,
    status integer NOT NULL,
    reject_reason character varying(200),
    owner_address character varying(128) NOT NULL,
    creator_address character varying(128) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    remaining_supply integer,
    blockchain_details text,
    deployment_tx_hash character varying(100),
    payment_details text,
    payment_confirmed boolean,
    payment_confirmed_at timestamp without time zone,
    approved_at timestamp without time zone,
    approved_by character varying(64),
    payment_tx_hash character varying(255),
    error_message text,
    deployment_in_progress boolean DEFAULT false,
    deployment_started_at timestamp without time zone,
    CONSTRAINT ck_annual_revenue_positive CHECK ((annual_revenue > (0)::double precision)),
    CONSTRAINT ck_area_positive CHECK ((area > (0)::double precision)),
    CONSTRAINT ck_status_valid CHECK ((status = ANY (ARRAY[1, 2, 3]))),
    CONSTRAINT ck_token_price_positive CHECK ((token_price > (0)::double precision)),
    CONSTRAINT ck_token_supply_positive CHECK ((token_supply > 0)),
    CONSTRAINT ck_total_value_positive CHECK ((total_value > (0)::double precision))
);


ALTER TABLE public.assets OWNER TO rwa_hub_user;

--
-- Name: assets_id_seq; Type: SEQUENCE; Schema: public; Owner: rwa_hub_user
--

CREATE SEQUENCE public.assets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.assets_id_seq OWNER TO rwa_hub_user;

--
-- Name: assets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rwa_hub_user
--

ALTER SEQUENCE public.assets_id_seq OWNED BY public.assets.id;


--
-- Name: commission_config; Type: TABLE; Schema: public; Owner: rwa_hub_user
--

CREATE TABLE public.commission_config (
    id integer NOT NULL,
    config_key character varying(100) NOT NULL,
    config_value text NOT NULL,
    description character varying(255),
    is_active boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.commission_config OWNER TO rwa_hub_user;

--
-- Name: commission_config_id_seq; Type: SEQUENCE; Schema: public; Owner: rwa_hub_user
--

CREATE SEQUENCE public.commission_config_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.commission_config_id_seq OWNER TO rwa_hub_user;

--
-- Name: commission_config_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rwa_hub_user
--

ALTER SEQUENCE public.commission_config_id_seq OWNED BY public.commission_config.id;


--
-- Name: commission_records; Type: TABLE; Schema: public; Owner: rwa_hub_user
--

CREATE TABLE public.commission_records (
    id integer NOT NULL,
    transaction_id integer NOT NULL,
    asset_id integer NOT NULL,
    recipient_address character varying(64) NOT NULL,
    amount double precision NOT NULL,
    currency character varying(10) NOT NULL,
    commission_type character varying(20) NOT NULL,
    status character varying(20) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    tx_hash character varying(100)
);


ALTER TABLE public.commission_records OWNER TO rwa_hub_user;

--
-- Name: commission_records_id_seq; Type: SEQUENCE; Schema: public; Owner: rwa_hub_user
--

CREATE SEQUENCE public.commission_records_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.commission_records_id_seq OWNER TO rwa_hub_user;

--
-- Name: commission_records_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rwa_hub_user
--

ALTER SEQUENCE public.commission_records_id_seq OWNED BY public.commission_records.id;


--
-- Name: commission_settings; Type: TABLE; Schema: public; Owner: rwa_hub_user
--

CREATE TABLE public.commission_settings (
    id integer NOT NULL,
    asset_type_id integer,
    commission_rate double precision NOT NULL,
    min_amount double precision,
    max_amount double precision,
    is_active boolean,
    created_by character varying(80),
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.commission_settings OWNER TO rwa_hub_user;

--
-- Name: commission_settings_id_seq; Type: SEQUENCE; Schema: public; Owner: rwa_hub_user
--

CREATE SEQUENCE public.commission_settings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.commission_settings_id_seq OWNER TO rwa_hub_user;

--
-- Name: commission_settings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rwa_hub_user
--

ALTER SEQUENCE public.commission_settings_id_seq OWNED BY public.commission_settings.id;


--
-- Name: commission_withdrawals; Type: TABLE; Schema: public; Owner: rwa_hub_user
--

CREATE TABLE public.commission_withdrawals (
    id integer NOT NULL,
    user_address character varying(64) NOT NULL,
    to_address character varying(64) NOT NULL,
    amount numeric(20,8) NOT NULL,
    currency character varying(10),
    status character varying(20) NOT NULL,
    delay_minutes integer,
    requested_at timestamp without time zone,
    process_at timestamp without time zone,
    processed_at timestamp without time zone,
    tx_hash character varying(80),
    gas_fee numeric(20,8),
    actual_amount numeric(20,8),
    note text,
    admin_note text,
    failure_reason text,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.commission_withdrawals OWNER TO rwa_hub_user;

--
-- Name: commission_withdrawals_id_seq; Type: SEQUENCE; Schema: public; Owner: rwa_hub_user
--

CREATE SEQUENCE public.commission_withdrawals_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.commission_withdrawals_id_seq OWNER TO rwa_hub_user;

--
-- Name: commission_withdrawals_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rwa_hub_user
--

ALTER SEQUENCE public.commission_withdrawals_id_seq OWNED BY public.commission_withdrawals.id;


--
-- Name: commissions; Type: TABLE; Schema: public; Owner: rwa_hub_user
--

CREATE TABLE public.commissions (
    id integer NOT NULL,
    user_id integer NOT NULL,
    asset_id integer NOT NULL,
    amount numeric(15,6) NOT NULL,
    tx_hash character varying(80),
    status character varying(20) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.commissions OWNER TO rwa_hub_user;

--
-- Name: commissions_id_seq; Type: SEQUENCE; Schema: public; Owner: rwa_hub_user
--

CREATE SEQUENCE public.commissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.commissions_id_seq OWNER TO rwa_hub_user;

--
-- Name: commissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rwa_hub_user
--

ALTER SEQUENCE public.commissions_id_seq OWNED BY public.commissions.id;


--
-- Name: dashboard_stats; Type: TABLE; Schema: public; Owner: rwa_hub_user
--

CREATE TABLE public.dashboard_stats (
    id integer NOT NULL,
    stat_date timestamp without time zone NOT NULL,
    stat_type character varying(50) NOT NULL,
    stat_value double precision,
    stat_period character varying(20) NOT NULL,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.dashboard_stats OWNER TO rwa_hub_user;

--
-- Name: dashboard_stats_id_seq; Type: SEQUENCE; Schema: public; Owner: rwa_hub_user
--

CREATE SEQUENCE public.dashboard_stats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dashboard_stats_id_seq OWNER TO rwa_hub_user;

--
-- Name: dashboard_stats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rwa_hub_user
--

ALTER SEQUENCE public.dashboard_stats_id_seq OWNED BY public.dashboard_stats.id;


--
-- Name: distribution_levels; Type: TABLE; Schema: public; Owner: rwa_hub_user
--

CREATE TABLE public.distribution_levels (
    id integer NOT NULL,
    level integer NOT NULL,
    commission_rate double precision NOT NULL,
    description text,
    is_active boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.distribution_levels OWNER TO rwa_hub_user;

--
-- Name: distribution_levels_id_seq; Type: SEQUENCE; Schema: public; Owner: rwa_hub_user
--

CREATE SEQUENCE public.distribution_levels_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.distribution_levels_id_seq OWNER TO rwa_hub_user;

--
-- Name: distribution_levels_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rwa_hub_user
--

ALTER SEQUENCE public.distribution_levels_id_seq OWNED BY public.distribution_levels.id;


--
-- Name: distribution_settings; Type: TABLE; Schema: public; Owner: rwa_hub_user
--

CREATE TABLE public.distribution_settings (
    id integer NOT NULL,
    level integer NOT NULL,
    commission_rate double precision NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.distribution_settings OWNER TO rwa_hub_user;

--
-- Name: distribution_settings_id_seq; Type: SEQUENCE; Schema: public; Owner: rwa_hub_user
--

CREATE SEQUENCE public.distribution_settings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.distribution_settings_id_seq OWNER TO rwa_hub_user;

--
-- Name: distribution_settings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rwa_hub_user
--

ALTER SEQUENCE public.distribution_settings_id_seq OWNED BY public.distribution_settings.id;


--
-- Name: dividend_distributions; Type: TABLE; Schema: public; Owner: rwa_hub_user
--

CREATE TABLE public.dividend_distributions (
    id integer NOT NULL,
    dividend_record_id integer NOT NULL,
    holder_address character varying(44) NOT NULL,
    amount numeric(20,6) NOT NULL,
    status character varying(20) NOT NULL,
    claimed_at timestamp without time zone,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.dividend_distributions OWNER TO rwa_hub_user;

--
-- Name: dividend_distributions_id_seq; Type: SEQUENCE; Schema: public; Owner: rwa_hub_user
--

CREATE SEQUENCE public.dividend_distributions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dividend_distributions_id_seq OWNER TO rwa_hub_user;

--
-- Name: dividend_distributions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rwa_hub_user
--

ALTER SEQUENCE public.dividend_distributions_id_seq OWNED BY public.dividend_distributions.id;


--
-- Name: dividend_records; Type: TABLE; Schema: public; Owner: rwa_hub_user
--

CREATE TABLE public.dividend_records (
    id integer NOT NULL,
    asset_id integer NOT NULL,
    amount numeric(20,6) NOT NULL,
    created_at timestamp without time zone,
    distributor_address character varying(44) NOT NULL,
    transaction_hash character varying(88),
    "interval" integer NOT NULL,
    updated_at timestamp without time zone
);


ALTER TABLE public.dividend_records OWNER TO rwa_hub_user;

--
-- Name: dividend_records_id_seq; Type: SEQUENCE; Schema: public; Owner: rwa_hub_user
--

CREATE SEQUENCE public.dividend_records_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dividend_records_id_seq OWNER TO rwa_hub_user;

--
-- Name: dividend_records_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rwa_hub_user
--

ALTER SEQUENCE public.dividend_records_id_seq OWNED BY public.dividend_records.id;


--
-- Name: dividends; Type: TABLE; Schema: public; Owner: rwa_hub_user
--

CREATE TABLE public.dividends (
    id integer NOT NULL,
    asset_id integer NOT NULL,
    amount numeric(20,6) NOT NULL,
    status character varying(50),
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    transaction_hash character varying(255),
    payment_token character varying(10),
    dividend_date timestamp without time zone,
    description text,
    error_message text
);


ALTER TABLE public.dividends OWNER TO rwa_hub_user;

--
-- Name: dividends_id_seq; Type: SEQUENCE; Schema: public; Owner: rwa_hub_user
--

CREATE SEQUENCE public.dividends_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dividends_id_seq OWNER TO rwa_hub_user;

--
-- Name: dividends_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rwa_hub_user
--

ALTER SEQUENCE public.dividends_id_seq OWNED BY public.dividends.id;


--
-- Name: holdings; Type: TABLE; Schema: public; Owner: rwa_hub_user
--

CREATE TABLE public.holdings (
    id integer NOT NULL,
    user_id integer NOT NULL,
    asset_id integer NOT NULL,
    quantity double precision NOT NULL,
    available_quantity double precision NOT NULL,
    staked_quantity double precision NOT NULL,
    purchase_price double precision,
    purchase_amount double precision,
    token_address character varying(100),
    blockchain character varying(20),
    is_on_chain boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.holdings OWNER TO rwa_hub_user;

--
-- Name: holdings_id_seq; Type: SEQUENCE; Schema: public; Owner: rwa_hub_user
--

CREATE SEQUENCE public.holdings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.holdings_id_seq OWNER TO rwa_hub_user;

--
-- Name: holdings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rwa_hub_user
--

ALTER SEQUENCE public.holdings_id_seq OWNED BY public.holdings.id;


--
-- Name: ip_visits; Type: TABLE; Schema: public; Owner: rwa_hub_user
--

CREATE TABLE public.ip_visits (
    id integer NOT NULL,
    ip_address character varying(45) NOT NULL,
    user_agent text,
    referer character varying(500),
    path character varying(500),
    "timestamp" timestamp without time zone NOT NULL,
    country character varying(100),
    city character varying(100)
);


ALTER TABLE public.ip_visits OWNER TO rwa_hub_user;

--
-- Name: ip_visits_id_seq; Type: SEQUENCE; Schema: public; Owner: rwa_hub_user
--

CREATE SEQUENCE public.ip_visits_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ip_visits_id_seq OWNER TO rwa_hub_user;

--
-- Name: ip_visits_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rwa_hub_user
--

ALTER SEQUENCE public.ip_visits_id_seq OWNED BY public.ip_visits.id;


--
-- Name: onchain_history; Type: TABLE; Schema: public; Owner: rwa_hub_user
--

CREATE TABLE public.onchain_history (
    id integer NOT NULL,
    asset_id integer NOT NULL,
    trade_id integer,
    trigger_type character varying(50) NOT NULL,
    onchain_type character varying(50) NOT NULL,
    status character varying(20) NOT NULL,
    transaction_hash character varying(100),
    block_number integer,
    gas_used integer,
    gas_price character varying(50),
    error_message text,
    retry_count integer,
    max_retries integer,
    triggered_by character varying(80),
    triggered_at timestamp without time zone NOT NULL,
    processed_at timestamp without time zone,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.onchain_history OWNER TO rwa_hub_user;

--
-- Name: onchain_history_id_seq; Type: SEQUENCE; Schema: public; Owner: rwa_hub_user
--

CREATE SEQUENCE public.onchain_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.onchain_history_id_seq OWNER TO rwa_hub_user;

--
-- Name: onchain_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rwa_hub_user
--

ALTER SEQUENCE public.onchain_history_id_seq OWNED BY public.onchain_history.id;


--
-- Name: platform_incomes; Type: TABLE; Schema: public; Owner: rwa_hub_user
--

CREATE TABLE public.platform_incomes (
    id integer NOT NULL,
    type integer NOT NULL,
    amount double precision NOT NULL,
    description character varying(200),
    asset_id integer,
    related_id integer,
    tx_hash character varying(100),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.platform_incomes OWNER TO rwa_hub_user;

--
-- Name: platform_incomes_id_seq; Type: SEQUENCE; Schema: public; Owner: rwa_hub_user
--

CREATE SEQUENCE public.platform_incomes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.platform_incomes_id_seq OWNER TO rwa_hub_user;

--
-- Name: platform_incomes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rwa_hub_user
--

ALTER SEQUENCE public.platform_incomes_id_seq OWNED BY public.platform_incomes.id;


--
-- Name: share_messages; Type: TABLE; Schema: public; Owner: rwa_hub_user
--

CREATE TABLE public.share_messages (
    id integer NOT NULL,
    content text NOT NULL,
    is_active boolean,
    weight integer,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.share_messages OWNER TO rwa_hub_user;

--
-- Name: COLUMN share_messages.content; Type: COMMENT; Schema: public; Owner: rwa_hub_user
--

COMMENT ON COLUMN public.share_messages.content IS '分享消息内容';


--
-- Name: COLUMN share_messages.is_active; Type: COMMENT; Schema: public; Owner: rwa_hub_user
--

COMMENT ON COLUMN public.share_messages.is_active IS '是否启用';


--
-- Name: COLUMN share_messages.weight; Type: COMMENT; Schema: public; Owner: rwa_hub_user
--

COMMENT ON COLUMN public.share_messages.weight IS '权重，用于随机选择时的概率';


--
-- Name: COLUMN share_messages.created_at; Type: COMMENT; Schema: public; Owner: rwa_hub_user
--

COMMENT ON COLUMN public.share_messages.created_at IS '创建时间';


--
-- Name: COLUMN share_messages.updated_at; Type: COMMENT; Schema: public; Owner: rwa_hub_user
--

COMMENT ON COLUMN public.share_messages.updated_at IS '更新时间';


--
-- Name: share_messages_id_seq; Type: SEQUENCE; Schema: public; Owner: rwa_hub_user
--

CREATE SEQUENCE public.share_messages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.share_messages_id_seq OWNER TO rwa_hub_user;

--
-- Name: share_messages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rwa_hub_user
--

ALTER SEQUENCE public.share_messages_id_seq OWNED BY public.share_messages.id;


--
-- Name: short_links; Type: TABLE; Schema: public; Owner: rwa_hub_user
--

CREATE TABLE public.short_links (
    id integer NOT NULL,
    code character varying(10) NOT NULL,
    original_url character varying(512) NOT NULL,
    created_at timestamp without time zone,
    expires_at timestamp without time zone,
    click_count integer,
    creator_address character varying(128)
);


ALTER TABLE public.short_links OWNER TO rwa_hub_user;

--
-- Name: short_links_id_seq; Type: SEQUENCE; Schema: public; Owner: rwa_hub_user
--

CREATE SEQUENCE public.short_links_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.short_links_id_seq OWNER TO rwa_hub_user;

--
-- Name: short_links_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rwa_hub_user
--

ALTER SEQUENCE public.short_links_id_seq OWNED BY public.short_links.id;


--
-- Name: system_configs; Type: TABLE; Schema: public; Owner: rwa_hub_user
--

CREATE TABLE public.system_configs (
    id integer NOT NULL,
    config_key character varying(50) NOT NULL,
    config_value text NOT NULL,
    description text,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.system_configs OWNER TO rwa_hub_user;

--
-- Name: system_configs_id_seq; Type: SEQUENCE; Schema: public; Owner: rwa_hub_user
--

CREATE SEQUENCE public.system_configs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.system_configs_id_seq OWNER TO rwa_hub_user;

--
-- Name: system_configs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rwa_hub_user
--

ALTER SEQUENCE public.system_configs_id_seq OWNED BY public.system_configs.id;


--
-- Name: trades; Type: TABLE; Schema: public; Owner: rwa_hub_user
--

CREATE TABLE public.trades (
    id integer NOT NULL,
    asset_id integer,
    type character varying(10) NOT NULL,
    amount integer NOT NULL,
    price double precision NOT NULL,
    trader_address character varying(64) NOT NULL,
    created_at timestamp without time zone,
    is_self_trade boolean NOT NULL,
    tx_hash character varying(100),
    status character varying(20) DEFAULT 'pending'::character varying,
    gas_used numeric,
    total double precision,
    fee double precision,
    fee_rate double precision,
    token_amount double precision,
    payment_details text
);


ALTER TABLE public.trades OWNER TO rwa_hub_user;

--
-- Name: trades_id_seq; Type: SEQUENCE; Schema: public; Owner: rwa_hub_user
--

CREATE SEQUENCE public.trades_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.trades_id_seq OWNER TO rwa_hub_user;

--
-- Name: trades_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rwa_hub_user
--

ALTER SEQUENCE public.trades_id_seq OWNED BY public.trades.id;


--
-- Name: transactions; Type: TABLE; Schema: public; Owner: rwa_hub_user
--

CREATE TABLE public.transactions (
    id integer NOT NULL,
    from_address character varying(255) NOT NULL,
    to_address character varying(255) NOT NULL,
    amount double precision NOT NULL,
    token_symbol character varying(50) NOT NULL,
    signature character varying(255),
    status character varying(50) NOT NULL,
    tx_type character varying(50) NOT NULL,
    data text,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.transactions OWNER TO rwa_hub_user;

--
-- Name: transactions_id_seq; Type: SEQUENCE; Schema: public; Owner: rwa_hub_user
--

CREATE SEQUENCE public.transactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.transactions_id_seq OWNER TO rwa_hub_user;

--
-- Name: transactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rwa_hub_user
--

ALTER SEQUENCE public.transactions_id_seq OWNED BY public.transactions.id;


--
-- Name: user_commission_balance; Type: TABLE; Schema: public; Owner: rwa_hub_user
--

CREATE TABLE public.user_commission_balance (
    id integer NOT NULL,
    user_address character varying(64) NOT NULL,
    total_earned numeric(20,8),
    available_balance numeric(20,8),
    withdrawn_amount numeric(20,8),
    frozen_amount numeric(20,8),
    currency character varying(10),
    last_updated timestamp without time zone,
    created_at timestamp without time zone
);


ALTER TABLE public.user_commission_balance OWNER TO rwa_hub_user;

--
-- Name: user_commission_balance_id_seq; Type: SEQUENCE; Schema: public; Owner: rwa_hub_user
--

CREATE SEQUENCE public.user_commission_balance_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_commission_balance_id_seq OWNER TO rwa_hub_user;

--
-- Name: user_commission_balance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rwa_hub_user
--

ALTER SEQUENCE public.user_commission_balance_id_seq OWNED BY public.user_commission_balance.id;


--
-- Name: user_referrals; Type: TABLE; Schema: public; Owner: rwa_hub_user
--

CREATE TABLE public.user_referrals (
    id integer NOT NULL,
    user_address character varying(64) NOT NULL,
    referrer_address character varying(64) NOT NULL,
    referral_level integer NOT NULL,
    referral_code character varying(50),
    joined_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    referral_time timestamp without time zone NOT NULL,
    asset_id integer,
    status character varying(20) NOT NULL
);


ALTER TABLE public.user_referrals OWNER TO rwa_hub_user;

--
-- Name: user_referrals_id_seq; Type: SEQUENCE; Schema: public; Owner: rwa_hub_user
--

CREATE SEQUENCE public.user_referrals_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_referrals_id_seq OWNER TO rwa_hub_user;

--
-- Name: user_referrals_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rwa_hub_user
--

ALTER SEQUENCE public.user_referrals_id_seq OWNED BY public.user_referrals.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: rwa_hub_user
--

CREATE TABLE public.users (
    id integer NOT NULL,
    username character varying(50) NOT NULL,
    email character varying(120) NOT NULL,
    password_hash character varying(128),
    eth_address character varying(64),
    nonce character varying(100),
    role character varying(20) NOT NULL,
    status character varying(20) NOT NULL,
    settings text,
    is_active boolean,
    last_login_at timestamp without time zone,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    solana_address character varying(64),
    wallet_type character varying(20),
    is_distributor boolean,
    is_verified boolean,
    is_blocked boolean,
    referrer_address character varying(64)
);


ALTER TABLE public.users OWNER TO rwa_hub_user;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: rwa_hub_user
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.users_id_seq OWNER TO rwa_hub_user;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rwa_hub_user
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: withdrawal_requests; Type: TABLE; Schema: public; Owner: rwa_hub_user
--

CREATE TABLE public.withdrawal_requests (
    id integer NOT NULL,
    user_address character varying(44) NOT NULL,
    amount numeric(20,6) NOT NULL,
    type character varying(20) NOT NULL,
    status character varying(20) NOT NULL,
    transaction_hash character varying(88),
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.withdrawal_requests OWNER TO rwa_hub_user;

--
-- Name: withdrawal_requests_id_seq; Type: SEQUENCE; Schema: public; Owner: rwa_hub_user
--

CREATE SEQUENCE public.withdrawal_requests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.withdrawal_requests_id_seq OWNER TO rwa_hub_user;

--
-- Name: withdrawal_requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: rwa_hub_user
--

ALTER SEQUENCE public.withdrawal_requests_id_seq OWNED BY public.withdrawal_requests.id;


--
-- Name: admin_operation_logs id; Type: DEFAULT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.admin_operation_logs ALTER COLUMN id SET DEFAULT nextval('public.admin_operation_logs_id_seq'::regclass);


--
-- Name: admin_users id; Type: DEFAULT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.admin_users ALTER COLUMN id SET DEFAULT nextval('public.admin_users_id_seq'::regclass);


--
-- Name: asset_status_history id; Type: DEFAULT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.asset_status_history ALTER COLUMN id SET DEFAULT nextval('public.asset_status_history_id_seq'::regclass);


--
-- Name: assets id; Type: DEFAULT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.assets ALTER COLUMN id SET DEFAULT nextval('public.assets_id_seq'::regclass);


--
-- Name: commission_config id; Type: DEFAULT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.commission_config ALTER COLUMN id SET DEFAULT nextval('public.commission_config_id_seq'::regclass);


--
-- Name: commission_records id; Type: DEFAULT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.commission_records ALTER COLUMN id SET DEFAULT nextval('public.commission_records_id_seq'::regclass);


--
-- Name: commission_settings id; Type: DEFAULT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.commission_settings ALTER COLUMN id SET DEFAULT nextval('public.commission_settings_id_seq'::regclass);


--
-- Name: commission_withdrawals id; Type: DEFAULT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.commission_withdrawals ALTER COLUMN id SET DEFAULT nextval('public.commission_withdrawals_id_seq'::regclass);


--
-- Name: commissions id; Type: DEFAULT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.commissions ALTER COLUMN id SET DEFAULT nextval('public.commissions_id_seq'::regclass);


--
-- Name: dashboard_stats id; Type: DEFAULT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.dashboard_stats ALTER COLUMN id SET DEFAULT nextval('public.dashboard_stats_id_seq'::regclass);


--
-- Name: distribution_levels id; Type: DEFAULT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.distribution_levels ALTER COLUMN id SET DEFAULT nextval('public.distribution_levels_id_seq'::regclass);


--
-- Name: distribution_settings id; Type: DEFAULT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.distribution_settings ALTER COLUMN id SET DEFAULT nextval('public.distribution_settings_id_seq'::regclass);


--
-- Name: dividend_distributions id; Type: DEFAULT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.dividend_distributions ALTER COLUMN id SET DEFAULT nextval('public.dividend_distributions_id_seq'::regclass);


--
-- Name: dividend_records id; Type: DEFAULT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.dividend_records ALTER COLUMN id SET DEFAULT nextval('public.dividend_records_id_seq'::regclass);


--
-- Name: dividends id; Type: DEFAULT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.dividends ALTER COLUMN id SET DEFAULT nextval('public.dividends_id_seq'::regclass);


--
-- Name: holdings id; Type: DEFAULT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.holdings ALTER COLUMN id SET DEFAULT nextval('public.holdings_id_seq'::regclass);


--
-- Name: ip_visits id; Type: DEFAULT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.ip_visits ALTER COLUMN id SET DEFAULT nextval('public.ip_visits_id_seq'::regclass);


--
-- Name: onchain_history id; Type: DEFAULT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.onchain_history ALTER COLUMN id SET DEFAULT nextval('public.onchain_history_id_seq'::regclass);


--
-- Name: platform_incomes id; Type: DEFAULT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.platform_incomes ALTER COLUMN id SET DEFAULT nextval('public.platform_incomes_id_seq'::regclass);


--
-- Name: share_messages id; Type: DEFAULT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.share_messages ALTER COLUMN id SET DEFAULT nextval('public.share_messages_id_seq'::regclass);


--
-- Name: short_links id; Type: DEFAULT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.short_links ALTER COLUMN id SET DEFAULT nextval('public.short_links_id_seq'::regclass);


--
-- Name: system_configs id; Type: DEFAULT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.system_configs ALTER COLUMN id SET DEFAULT nextval('public.system_configs_id_seq'::regclass);


--
-- Name: trades id; Type: DEFAULT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.trades ALTER COLUMN id SET DEFAULT nextval('public.trades_id_seq'::regclass);


--
-- Name: transactions id; Type: DEFAULT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.transactions ALTER COLUMN id SET DEFAULT nextval('public.transactions_id_seq'::regclass);


--
-- Name: user_commission_balance id; Type: DEFAULT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.user_commission_balance ALTER COLUMN id SET DEFAULT nextval('public.user_commission_balance_id_seq'::regclass);


--
-- Name: user_referrals id; Type: DEFAULT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.user_referrals ALTER COLUMN id SET DEFAULT nextval('public.user_referrals_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: withdrawal_requests id; Type: DEFAULT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.withdrawal_requests ALTER COLUMN id SET DEFAULT nextval('public.withdrawal_requests_id_seq'::regclass);


--
-- Data for Name: admin_operation_logs; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

COPY public.admin_operation_logs (id, admin_address, operation_type, target_table, target_id, operation_details, ip_address, created_at) FROM stdin;
1	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	更新分销等级	level	2	{"method": "PUT", "url": "/api/admin/v2/distribution-levels/2", "args": {}, "body": {"level": 2, "commission_rate": 15, "description": "\\u4e8c\\u7ea7\\u5206\\u9500", "is_active": true}, "status_code": 200}	127.0.0.1	2025-03-16 18:16:45.33315
2	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	更新分销等级	level	3	{"method": "PUT", "url": "/api/admin/v2/distribution-levels/3", "args": {}, "body": {"level": 3, "commission_rate": 5, "description": "\\u4e09\\u7ea7\\u5206\\u9500", "is_active": true}, "status_code": 200}	127.0.0.1	2025-03-16 18:17:31.881178
\.


--
-- Data for Name: admin_users; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

COPY public.admin_users (id, wallet_address, username, role, permissions, last_login, created_at, updated_at) FROM stdin;
1	0x123456789012345678901234567890123456abcd	超级管理员	super_admin	{管理用户,管理资产,管理佣金,审核资产,管理设置,管理管理员,查看日志,管理仪表盘}	\N	2025-03-16 03:38:52.807818	2025-03-16 03:38:52.809264
2	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	SOL管理员	super_admin	{管理用户,管理资产,管理佣金,审核资产,管理设置,管理管理员,查看日志,管理仪表盘}	\N	2025-03-16 03:50:02.624455	2025-03-16 03:50:02.62512
\.


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

COPY public.alembic_version (version_num) FROM stdin;
ce5a4d540c25
\.


--
-- Data for Name: asset_status_history; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

COPY public.asset_status_history (id, asset_id, old_status, new_status, change_time, change_reason) FROM stdin;
\.


--
-- Data for Name: assets; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

COPY public.assets (id, name, description, asset_type, location, area, total_value, token_symbol, token_price, token_supply, token_address, annual_revenue, images, documents, status, reject_reason, owner_address, creator_address, created_at, updated_at, deleted_at, remaining_supply, blockchain_details, deployment_tx_hash, payment_details, payment_confirmed, payment_confirmed_at, approved_at, approved_by, payment_tx_hash, error_message, deployment_in_progress, deployment_started_at) FROM stdin;
4	BTC ETF	BTC ETF (Bitcoin Exchange-Traded Fund) is a financial instrument that allows investors to gain exposure to Bitcoin through traditional stock markets. By tracking the price of Bitcoin, it provides a convenient, secure, and compliant way for investors to participate in the cryptocurrency market without directly holding Bitcoin.	20	COINBASE	\N	10000000	RH-205874	0.1	100000000	\N	1000000	["/static/uploads/20/temp/image/1740499081_premier-etf-bitcoin.jpg"]	\N	1	\N	0x6394993426dba3b654ef0052698fe9e0b6a98870	0x6394993426dba3b654ef0052698fe9e0b6a98870	2025-02-25 15:58:03.462315	2025-03-12 15:39:36.018243	\N	100000000	\N	\N	\N	\N	\N	\N	\N	\N	\N	f	\N
2	Palm Jumeirah Luxury Villa 8101	This villa is located on Palm Jumeirah in Dubai, with a private pool and beach, luxurious interiors, making it an ideal choice for high-end living.	10	8101 Palm Jumeirah Road, Dubai, UAE	4000	23000000	RH-109774	0.575	40000000	\N	120000	["/static/uploads/10/temp/image/1740481324_DSC_1851_103.jpg", "/static/uploads/10/temp/image/1740481328_Frond-M-Palm-Jumeirah-Dubai-Dubai-United-Arab-Emirates-20.jpg", "/static/uploads/10/temp/image/1740481328_Frond-M-Palm-Jumeirah-Dubai-Dubai-United-Arab-Emirates-1.jpg", "/static/uploads/10/temp/image/1740481328_Frond-M-Palm-Jumeirah-Dubai-Dubai-United-Arab-Emirates-21.jpg", "/static/uploads/10/temp/image/1740481328_DSC_3828_51-Copy-Copy-2.jpg", "/static/uploads/10/temp/image/1740481332_1100xxs.webp", "/static/uploads/10/temp/image/1740481332_922248_38433.webp"]	\N	2	\N	0x6394993426dba3b654ef0052698fe9e0b6a98870	0x6394993426dba3b654ef0052698fe9e0b6a98870	2025-02-25 11:02:27.595321	2025-03-16 20:18:04.541537	\N	39999867	\N	\N	\N	\N	\N	\N	\N	\N	\N	f	\N
3	BTC ETF	BTC ETF (Bitcoin Exchange-Traded Fund) is a financial instrument that allows investors to gain exposure to Bitcoin through traditional stock markets. By tracking the price of Bitcoin, it provides a convenient, secure, and compliant way for investors to participate in the cryptocurrency market without directly holding Bitcoin.	20	COINBASE	\N	100000000	RH-209003	1	100000000	\N	1000000	["/static/uploads/20/temp/image/1740481479_premier-etf-bitcoin.jpg"]	\N	1	\N	0x6394993426dba3b654ef0052698fe9e0b6a98870	0x6394993426dba3b654ef0052698fe9e0b6a98870	2025-02-25 11:04:51.732714	2025-03-12 15:39:36.018242	\N	100000000	\N	\N	\N	\N	\N	\N	\N	\N	\N	f	\N
10	Palm Jumeirah Luxury Villa 8101	12332	10	8101 Palm Jumeirah Road, Dubai, UAE	12311	12312311	RH-101727	0.100011	123110000	So7gwf7Pc4Dtawbi7Ee7TeSiLjUMh6AyLqCH4ZxL3n	1	["/static/uploads/10/RH-101727_1_1740518175_photo-1586773860363-8ec8703e6aa5.jpeg", "/static/uploads/10/RH-101727_2_1740518175_photo-1587351021759-3e566b6af7cc.jpeg", "/static/uploads/10/RH-101727_3_1740518162_photo-1587351021355-a479a299d2f9.jpeg", "/static/uploads/10/RH-101727_4_1740518195_photo-1581982231900-6a1a46b744c9.jpeg"]	[{"name": "DeepSeek\\u4ece\\u5165\\u95e8\\u5230\\u7cbe\\u901a(20250204).pdf", "url": "/static/uploads/projects/RH-205710/documents/file_1742235293349_1.pdf"}]	2	\N	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-18 13:49:50.843079	2025-03-18 13:49:50.843083	\N	123110000	{"network": "solana", "token_type": "spl", "decimals": 9, "deployment_time": "2025-03-18T21:49:50.841529"}	\N	\N	f	\N	\N	\N	\N	\N	f	\N
11	Palm Jumeirah Luxury Villa 8101	12332	10	8101 Palm Jumeirah Road, Dubai, UAE	12311	123123111	RH-101409	1.000106	123110000	SoEDfdgwDYLGr5TkrXdQ3bRAwi11jo7FCdeJboeAMi	1	["/static/uploads/10/RH-101409_1_1740518175_photo-1586773860363-8ec8703e6aa5.jpeg", "/static/uploads/10/RH-101409_2_1740518175_photo-1587351021759-3e566b6af7cc.jpeg", "/static/uploads/10/RH-101409_3_1740518162_photo-1587351021355-a479a299d2f9.jpeg", "/static/uploads/10/RH-101409_4_1740518195_photo-1581982231900-6a1a46b744c9.jpeg", "/static/uploads/10/RH-101409_5_1740518195_photo-1583830379747-195159d0de82.jpeg", "/static/uploads/10/RH-101409_6_1740518175_photo-1586534738560-438efdf1d205.jpeg", "/static/uploads/10/RH-101409_7_1740518175_photo-1583953458882-302655b5c376.jpeg", "/static/uploads/10/RH-101409_8_1740518175_photo-1586773860363-8ec8703e6aa5.jpeg", "/static/uploads/10/RH-101409_9_1740518175_photo-1587351021759-3e566b6af7cc.jpeg"]	\N	2	\N	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-18 17:45:50.481989	2025-03-18 17:45:50.481991	\N	123110000	{"network": "solana", "token_type": "spl", "decimals": 9, "deployment_time": "2025-03-19T01:45:50.477362"}	\N	\N	f	\N	\N	\N	\N	\N	f	\N
16	自动化测试资产	用于验证自动上链系统的测试资产	20	测试地址	\N	1000	RH-209999	1	1000	\N	100	\N	\N	1	\N	11111111111111111111111111111111	11111111111111111111111111111111	2025-05-27 11:43:49.310431	2025-05-27 03:43:49.311541	\N	1000	\N	\N	\N	f	\N	\N	\N	test_tx_hash_1748317429	\N	f	\N
20	Siberian Green Energy BTC Mining Center	绿色能源比特币挖矿中心测试资产	10	Siberia, Russia	5000	100000	RH-209342	100	50000000	\N	10000	\N	\N	2	\N	6UrwhN2rqQvo2tBfc9FZCdUbt9JLs3BJiEm7pv4NM41b	6UrwhN2rqQvo2tBfc9FZCdUbt9JLs3BJiEm7pv4NM41b	2025-05-27 13:36:03.806223	2025-07-23 04:16:02.277581	\N	50000000	\N	\N	\N	f	\N	\N	\N	\N	\N	f	\N
13	Palm Jumeirah Luxury Villa 8101	1221	10	8101 Palm Jumeirah Road, Dubai, UAE	121	1212	RH-106046	0.001002	1210000	SoDiVXmWXx65ueRKTEUjzcWMMGg43RCjhG5cA6vfTV	1	["/static/uploads/10/RH-106046_1_1740518175_photo-1586773860363-8ec8703e6aa5.jpeg", "/static/uploads/10/RH-106046_2_1740518175_photo-1587351021759-3e566b6af7cc.jpeg", "/static/uploads/10/RH-106046_3_1740518162_photo-1587351021355-a479a299d2f9.jpeg", "/static/uploads/10/RH-106046_4_1740518195_photo-1581982231900-6a1a46b744c9.jpeg"]	\N	2	\N	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-20 09:37:03.21499	2025-03-20 09:37:03.214994	\N	1210000	{"network": "solana", "token_type": "spl", "decimals": 9, "deployment_time": "2025-03-20T17:37:03.213900"}	\N	\N	f	\N	\N	\N	\N	\N	f	\N
9	Palm Jumeirah Luxury Villa 8101	12332	10	8101 Palm Jumeirah Road, Dubai, UAE	12311	12312311	RH-101719	0.100011	123110000	So7AoJw2CAEj3GL73eZo7YVbqhfDDvN5w3aerk5o4j	1	["/static/uploads/10/RH-101719_1_1740518175_photo-1586773860363-8ec8703e6aa5.jpeg", "/static/uploads/10/RH-101719_2_1740518175_photo-1587351021759-3e566b6af7cc.jpeg", "/static/uploads/10/RH-101719_3_1740518162_photo-1587351021355-a479a299d2f9.jpeg", "/static/uploads/10/RH-101719_4_1740518195_photo-1581982231900-6a1a46b744c9.jpeg"]	[{"name": "DeepSeek\\u4ece\\u5165\\u95e8\\u5230\\u7cbe\\u901a(20250204).pdf", "url": "/static/uploads/projects/RH-205710/documents/file_1742235293349_1.pdf"}]	2	\N	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-18 13:46:40.222996	2025-03-18 13:46:40.223001	\N	123110000	{"network": "solana", "token_type": "spl", "decimals": 9, "deployment_time": "2025-03-18T21:46:40.218740"}	\N	\N	f	\N	\N	\N	\N	\N	f	\N
12	Palm Jumeirah Luxury Villa 8101	1221	10	8101 Palm Jumeirah Road, Dubai, UAE	121	1212	RH-106451	0.001002	1210000	SoENL8Pp914uyP4uFquKTTsYEkKyVdwdSE82H9zPN4	1	["/static/uploads/10/RH-106451_1_1740518175_photo-1586773860363-8ec8703e6aa5.jpeg", "/static/uploads/10/RH-106451_2_1740518175_photo-1587351021759-3e566b6af7cc.jpeg", "/static/uploads/10/RH-106451_3_1740518162_photo-1587351021355-a479a299d2f9.jpeg", "/static/uploads/10/RH-106451_4_1740518195_photo-1581982231900-6a1a46b744c9.jpeg"]	\N	2	\N	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-20 09:36:23.665072	2025-03-20 09:36:23.665076	\N	1210000	{"network": "solana", "token_type": "spl", "decimals": 9, "deployment_time": "2025-03-20T17:36:23.660910"}	\N	\N	f	\N	\N	\N	\N	\N	f	\N
14	Palm Jumeirah Luxury Villa 8101	1221	10	8101 Palm Jumeirah Road, Dubai, UAE	121	111	RH-102535	9.2e-05	1210000	So6Uxagq4JuofKZvK2GQqifAkbz5Km6qbeXJhHmRCo	1	["/static/uploads/10/RH-102535_1_1740518175_photo-1586773860363-8ec8703e6aa5.jpeg", "/static/uploads/10/RH-102535_2_1740518175_photo-1587351021759-3e566b6af7cc.jpeg", "/static/uploads/10/RH-102535_3_1740518162_photo-1587351021355-a479a299d2f9.jpeg", "/static/uploads/10/RH-102535_4_1740518195_photo-1581982231900-6a1a46b744c9.jpeg"]	\N	2	\N	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-21 08:56:53.946317	2025-03-21 08:56:53.946321	\N	1210000	{"network": "solana", "token_type": "spl", "decimals": 9, "deployment_time": "2025-03-21T16:56:53.942959"}	\N	{"tx_hash": "0xeff1b4d8e6538eb754174c73c6769434f48189b0b130fd2af1030992c4280804", "platform_address": "HnPZkg9FpHjovNNZ8Au1MyLjYPbW9KsK87ACPCh1SvSd"}	t	2025-03-21 08:56:53.942988	\N	\N	\N	\N	f	\N
\.


--
-- Data for Name: commission_config; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

COPY public.commission_config (id, config_key, config_value, description, is_active, created_at, updated_at) FROM stdin;
1	commission_rate	35.0	推荐佣金比例	t	2025-05-26 15:51:19.283657	2025-05-26 15:52:41.620056
4	test_rate	25.0	测试佣金比例	t	2025-05-26 15:58:03.675046	2025-05-26 16:14:14.551115
2	min_withdraw_amount	10.0	最低提现金额	t	2025-05-26 15:51:19.287361	2025-05-26 16:14:14.739578
3	withdraw_delay_minutes	1	提现延迟分钟数	t	2025-05-26 15:51:19.288302	2025-05-26 16:14:14.740922
\.


--
-- Data for Name: commission_records; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

COPY public.commission_records (id, transaction_id, asset_id, recipient_address, amount, currency, commission_type, status, created_at, updated_at, tx_hash) FROM stdin;
1	96	2	0x0000000000000000000000000000000000000000	0.020125	USDC	platform	paid	2025-03-16 20:00:37.830593	2025-03-16 20:00:40.892893	\N
2	97	2	0x0000000000000000000000000000000000000000	0.020125	USDC	platform	paid	2025-03-16 20:01:53.040746	2025-03-16 20:01:56.056418	\N
3	98	2	0x0000000000000000000000000000000000000000	0.020125	USDC	platform	pending	2025-03-16 20:03:03.035035	2025-03-16 20:03:03.035039	\N
4	98	2	0x0000000000000000000000000000000000000000	0.020125	USDC	platform	pending	2025-03-16 20:03:06.06698	2025-03-16 20:03:06.066981	\N
5	99	2	0x0000000000000000000000000000000000000000	0.020125	USDC	platform	pending	2025-03-16 20:03:57.007667	2025-03-16 20:03:57.00767	\N
6	99	2	0x0000000000000000000000000000000000000000	0.020125	USDC	platform	pending	2025-03-16 20:04:00.028448	2025-03-16 20:04:00.028451	\N
7	100	2	0x0000000000000000000000000000000000000000	0.020125	USDC	platform	pending	2025-03-16 20:05:36.956965	2025-03-16 20:05:36.95697	\N
8	100	2	0x0000000000000000000000000000000000000000	0.020125	USDC	platform	pending	2025-03-16 20:05:39.980039	2025-03-16 20:05:39.98004	\N
9	101	2	0x0000000000000000000000000000000000000000	0.04025	USDC	platform	pending	2025-03-16 20:06:02.05244	2025-03-16 20:06:02.052444	\N
10	101	2	0x0000000000000000000000000000000000000000	0.04025	USDC	platform	pending	2025-03-16 20:06:05.081278	2025-03-16 20:06:05.081279	\N
11	102	2	0x0000000000000000000000000000000000000000	0.020125	USDC	platform	pending	2025-03-16 20:06:47.68625	2025-03-16 20:06:47.686254	\N
12	102	2	0x0000000000000000000000000000000000000000	0.020125	USDC	platform	pending	2025-03-16 20:06:50.721114	2025-03-16 20:06:50.721117	\N
13	103	2	0x0000000000000000000000000000000000000000	0.020125	USDC	platform	pending	2025-03-16 20:08:30.620089	2025-03-16 20:08:30.620092	\N
14	103	2	0x0000000000000000000000000000000000000000	0.020125	USDC	platform	pending	2025-03-16 20:08:33.659603	2025-03-16 20:08:33.659604	\N
15	104	2	0x0000000000000000000000000000000000000000	0.04025	USDC	platform	pending	2025-03-16 20:18:01.512802	2025-03-16 20:18:01.512805	\N
16	104	2	0x0000000000000000000000000000000000000000	0.04025	USDC	platform	pending	2025-03-16 20:18:04.5451	2025-03-16 20:18:04.545105	\N
17	107	10	0x0000000000000000000000000000000000000000	0.0100011	USDC	platform	pending	2025-03-18 16:04:36.798615	2025-03-18 16:04:36.798617	\N
18	108	10	0x0000000000000000000000000000000000000000	0.000300033	USDC	platform	pending	2025-03-18 16:07:08.196015	2025-03-18 16:07:08.196024	\N
19	109	2	0x0000000000000000000000000000000000000000	0.221375	USDC	platform	pending	2025-03-18 18:58:40.799338	2025-03-18 18:58:40.799342	\N
20	110	11	0x0000000000000000000000000000000000000000	0.1000106	USDC	platform	pending	2025-03-19 00:32:03.583357	2025-03-19 00:32:03.58336	\N
21	111	2	0x0000000000000000000000000000000000000000	0.057499999999999996	USDC	platform	pending	2025-03-19 12:47:21.152128	2025-03-19 12:47:21.152132	\N
22	112	13	0x0000000000000000000000000000000000000000	0.0035070000000000006	USDC	platform	pending	2025-03-21 03:37:17.605012	2025-03-21 03:37:17.605018	\N
23	113	14	0x0000000000000000000000000000000000000000	0.000322	USDC	platform	pending	2025-03-21 14:10:19.312951	2025-03-21 14:10:19.312952	\N
24	114	14	0x0000000000000000000000000000000000000000	0.00045080000000000006	USDC	platform	pending	2025-03-21 14:12:21.058048	2025-03-21 14:12:21.058051	\N
\.


--
-- Data for Name: commission_settings; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

COPY public.commission_settings (id, asset_type_id, commission_rate, min_amount, max_amount, is_active, created_by, created_at, updated_at) FROM stdin;
1	\N	0.01	100	1000000	t	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-16 15:52:02.655307	2025-03-16 15:52:02.655311
2	10	0.01	100	2000000	t	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-16 15:52:02.655312	2025-03-16 15:52:02.655312
3	20	0.01	100	3000000	t	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-16 15:52:02.655312	2025-03-16 15:52:02.655314
\.


--
-- Data for Name: commission_withdrawals; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

COPY public.commission_withdrawals (id, user_address, to_address, amount, currency, status, delay_minutes, requested_at, process_at, processed_at, tx_hash, gas_fee, actual_amount, note, admin_note, failure_reason, created_at, updated_at) FROM stdin;
2	0x1234567890123456789012345678901234567890	0x9876543210987654321098765432109876543210	25.75000000	USDC	completed	1	2025-05-26 15:58:03.762016	2025-05-26 15:59:03.762016	2025-05-26 15:58:03.767806	0xabcdef123456	0.05000000	25.70000000	\N	\N	\N	2025-05-26 15:58:03.762659	2025-05-26 15:58:03.767813
3	0x1234567890123456789012345678901234567890	0x9876543210987654321098765432109876543210	25.75000000	USDC	completed	1	2025-05-26 16:10:52.203642	2025-05-26 16:11:52.203642	2025-05-26 16:10:52.208326	0xabcdef123456	0.05000000	25.70000000	\N	\N	\N	2025-05-26 16:10:52.204212	2025-05-26 16:10:52.208333
4	0xtest123456789012345678901234567890	0xwithdraw123456789012345678901234567890	30.00000000	USDC	pending	1	2025-05-26 16:10:52.309884	2025-05-26 16:11:52.309884	\N	\N	0.00000000	\N	\N	\N	\N	2025-05-26 16:10:52.310411	2025-05-26 16:10:52.310411
5	0x1234567890123456789012345678901234567890	0x9876543210987654321098765432109876543210	25.75000000	USDC	completed	1	2025-05-26 16:12:19.467319	2025-05-26 16:13:19.467319	2025-05-26 16:12:19.471864	0xabcdef123456	0.05000000	25.70000000	\N	\N	\N	2025-05-26 16:12:19.468031	2025-05-26 16:12:19.471871
6	0xtest123456789012345678901234567890	0xwithdraw123456789012345678901234567890	30.00000000	USDC	completed	1	2025-05-26 16:12:19.568979	2025-05-26 16:13:19.568979	2025-05-26 16:12:19.572673	0xtxhash123456	0.05000000	29.95000000	\N	\N	\N	2025-05-26 16:12:19.569347	2025-05-26 16:12:19.572678
7	0x1234567890123456789012345678901234567890	0x9876543210987654321098765432109876543210	25.75000000	USDC	completed	1	2025-05-26 16:14:14.642972	2025-05-26 16:15:14.642972	2025-05-26 16:14:14.646758	0xabcdef123456	0.05000000	25.70000000	\N	\N	\N	2025-05-26 16:14:14.643646	2025-05-26 16:14:14.646767
8	0xtest123456789012345678901234567890	0xwithdraw123456789012345678901234567890	30.00000000	USDC	completed	1	2025-05-26 16:14:14.743154	2025-05-26 16:15:14.743154	2025-05-26 16:14:14.747257	0xtxhash123456	0.05000000	29.95000000	\N	\N	\N	2025-05-26 16:14:14.743505	2025-05-26 16:14:14.747262
\.


--
-- Data for Name: commissions; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

COPY public.commissions (id, user_id, asset_id, amount, tx_hash, status, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: dashboard_stats; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

COPY public.dashboard_stats (id, stat_date, stat_type, stat_value, stat_period, created_at, updated_at) FROM stdin;
8	2025-03-16 00:00:00	user_count	0	daily	2025-03-16 18:34:58.077985	2025-03-16 20:18:04.548289
13	2025-03-16 00:00:00	new_users	0	daily	2025-03-16 18:34:58.10194	2025-03-16 20:18:04.551652
9	2025-03-16 00:00:00	asset_count	3	daily	2025-03-16 18:34:58.09019	2025-03-16 20:18:04.562156
10	2025-03-16 00:00:00	asset_value	133000000	daily	2025-03-16 18:34:58.09259	2025-03-16 20:18:04.57139
11	2025-03-16 00:00:00	trade_count	16	daily	2025-03-16 18:34:58.099316	2025-03-16 20:18:04.576327
12	2025-03-16 00:00:00	trade_volume	12.075000000000001	daily	2025-03-16 18:34:58.10129	2025-03-16 20:18:04.578496
32	2025-03-21 00:00:00	user_count	0	daily	2025-03-21 03:37:17.602813	2025-03-21 14:12:21.039107
33	2025-03-21 00:00:00	new_users	0	daily	2025-03-21 03:37:17.610542	2025-03-21 14:12:21.041975
34	2025-03-21 00:00:00	asset_count	9	daily	2025-03-21 03:37:17.61548	2025-03-21 14:12:21.044418
35	2025-03-21 00:00:00	asset_value	280750268	daily	2025-03-21 03:37:17.618984	2025-03-21 14:12:21.046353
36	2025-03-21 00:00:00	trade_count	2	daily	2025-03-21 03:37:17.623504	2025-03-21 14:12:21.048223
37	2025-03-21 00:00:00	trade_volume	0.10940000000000001	daily	2025-03-21 03:37:17.625231	2025-03-21 14:12:21.04977
2	2025-03-17 00:00:00	user_count	0	daily	2025-03-17 02:32:17.734643	2025-03-17 19:35:48.82534
3	2025-03-17 00:00:00	new_users	0	daily	2025-03-17 02:32:24.493575	2025-03-17 19:35:48.8333
4	2025-03-17 00:00:00	asset_count	4	daily	2025-03-17 02:32:24.493575	2025-03-17 19:35:48.837697
5	2025-03-17 00:00:00	asset_value	134231233.89	daily	2025-03-17 02:32:24.493575	2025-03-17 19:35:48.839435
6	2025-03-17 00:00:00	trade_count	2	daily	2025-03-17 02:32:24.493575	2025-03-17 19:35:48.841813
7	2025-03-17 00:00:00	trade_volume	1.7249999999999999	daily	2025-03-17 02:32:24.493575	2025-03-17 19:35:48.843419
14	2025-03-18 00:00:00	user_count	0	daily	2025-03-18 12:40:44.432239	2025-03-18 18:58:40.781176
15	2025-03-18 00:00:00	new_users	0	daily	2025-03-18 12:40:44.436836	2025-03-18 18:58:40.799953
16	2025-03-18 00:00:00	asset_count	6	daily	2025-03-18 12:40:44.439589	2025-03-18 18:58:40.802839
17	2025-03-18 00:00:00	asset_value	280747733	daily	2025-03-18 12:40:44.441381	2025-03-18 18:58:40.804704
18	2025-03-18 00:00:00	trade_count	3	daily	2025-03-18 12:40:44.44385	2025-03-18 18:58:40.808349
19	2025-03-18 00:00:00	trade_volume	16.626133	daily	2025-03-18 12:40:44.444978	2025-03-18 18:58:40.810642
20	2025-03-19 00:00:00	user_count	0	daily	2025-03-19 00:32:03.580958	2025-03-19 12:47:21.143389
21	2025-03-19 00:00:00	new_users	0	daily	2025-03-19 00:32:03.584454	2025-03-19 12:47:21.152303
22	2025-03-19 00:00:00	asset_count	6	daily	2025-03-19 00:32:03.586719	2025-03-19 12:47:21.156536
23	2025-03-19 00:00:00	asset_value	280747733	daily	2025-03-19 00:32:03.589216	2025-03-19 12:47:21.159381
24	2025-03-19 00:00:00	trade_count	2	daily	2025-03-19 00:32:03.591301	2025-03-19 12:47:21.165432
25	2025-03-19 00:00:00	trade_volume	157.51059999999998	daily	2025-03-19 00:32:03.593033	2025-03-19 12:47:21.170058
26	2025-03-20 00:00:00	user_count	0	daily	2025-03-20 09:36:23.691591	2025-03-20 09:37:03.218559
27	2025-03-20 00:00:00	new_users	0	daily	2025-03-20 09:36:23.697266	2025-03-20 09:37:03.222297
28	2025-03-20 00:00:00	asset_count	8	daily	2025-03-20 09:36:23.701811	2025-03-20 09:37:03.226454
29	2025-03-20 00:00:00	asset_value	280750157	daily	2025-03-20 09:36:23.703873	2025-03-20 09:37:03.228903
30	2025-03-20 00:00:00	trade_count	0	daily	2025-03-20 09:36:23.708201	2025-03-20 09:37:03.230947
31	2025-03-20 00:00:00	trade_volume	0	daily	2025-03-20 09:36:23.70981	2025-03-20 09:37:03.232458
\.


--
-- Data for Name: distribution_levels; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

COPY public.distribution_levels (id, level, commission_rate, description, is_active, created_at, updated_at) FROM stdin;
1	1	30	一级分销	t	2025-03-16 15:52:02.662182	2025-03-16 15:52:02.662184
2	2	15	二级分销	t	2025-03-16 15:52:02.662185	2025-03-16 18:16:45.327171
3	3	5	三级分销	t	2025-03-16 15:52:02.662185	2025-03-16 18:17:31.878761
\.


--
-- Data for Name: distribution_settings; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

COPY public.distribution_settings (id, level, commission_rate, is_active, created_at, updated_at) FROM stdin;
1	1	0.3	t	2025-03-17 03:58:30.745188	2025-03-17 03:58:30.745188
2	2	0.15	t	2025-03-17 03:58:30.745188	2025-03-17 03:58:30.745188
3	3	0.05	t	2025-03-17 03:58:30.745188	2025-03-17 03:58:30.745188
\.


--
-- Data for Name: dividend_distributions; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

COPY public.dividend_distributions (id, dividend_record_id, holder_address, amount, status, claimed_at, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: dividend_records; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

COPY public.dividend_records (id, asset_id, amount, created_at, distributor_address, transaction_hash, "interval", updated_at) FROM stdin;
\.


--
-- Data for Name: dividends; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

COPY public.dividends (id, asset_id, amount, status, created_at, updated_at, transaction_hash, payment_token, dividend_date, description, error_message) FROM stdin;
\.


--
-- Data for Name: holdings; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

COPY public.holdings (id, user_id, asset_id, quantity, available_quantity, staked_quantity, purchase_price, purchase_amount, token_address, blockchain, is_on_chain, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: ip_visits; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

COPY public.ip_visits (id, ip_address, user_agent, referer, path, "timestamp", country, city) FROM stdin;
1	127.0.0.1	Werkzeug/2.3.7	\N	/api/share-messages/random	2025-05-31 05:08:40.176201	\N	\N
2	127.0.0.1	Werkzeug/2.3.7	\N	/api/shortlink/create	2025-05-31 05:08:40.184341	\N	\N
3	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	\N	/	2025-07-08 19:52:37.56404	\N	\N
4	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	http://127.0.0.1:5001/	/assets/	2025-07-08 19:52:43.755857	\N	\N
5	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	http://127.0.0.1:5001/assets/	/assets/RH-102535	2025-07-08 19:52:47.663334	\N	\N
6	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	http://127.0.0.1:5001/assets/RH-102535	/api/assets/symbol/RH-102535/dividend_stats	2025-07-08 19:52:47.831801	\N	\N
7	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	http://127.0.0.1:5001/assets/RH-102535	/api/trades	2025-07-08 19:52:47.833951	\N	\N
8	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	\N	/v6	2025-07-08 19:54:21.342048	\N	\N
9	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	http://127.0.0.1:5001/v6	/assets	2025-07-08 19:55:47.970501	\N	\N
10	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	http://127.0.0.1:5001/v6	/assets/	2025-07-08 19:55:47.985961	\N	\N
11	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	http://127.0.0.1:5001/v6	/portfolio	2025-07-08 19:55:52.32123	\N	\N
12	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	http://127.0.0.1:5001/v6	/admin/login	2025-07-08 19:56:35.528298	\N	\N
13	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	http://127.0.0.1:5001/v6	/admin/v2/login	2025-07-08 19:56:35.540761	\N	\N
14	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	http://127.0.0.1:5001/v6	/admin/register	2025-07-08 19:56:44.603913	\N	\N
15	192.168.0.200	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	\N	/	2025-07-08 20:08:44.225855	\N	\N
16	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	\N	/	2025-07-08 20:08:51.728559	\N	\N
17	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	\N	/v6	2025-07-08 20:09:01.314145	\N	\N
18	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	\N	/v6	2025-07-08 20:15:34.195317	\N	\N
19	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	\N	/v6	2025-07-08 20:15:36.284499	\N	\N
20	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	\N	/	2025-07-08 20:15:51.212081	\N	\N
21	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	\N	/v6	2025-07-08 20:16:19.007235	\N	\N
22	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	\N	/v6	2025-07-08 21:38:11.270899	\N	\N
23	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	\N	/	2025-07-08 21:38:24.069179	\N	\N
24	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	\N	/v6	2025-07-08 21:38:28.766814	\N	\N
25	127.0.0.1	curl/8.7.1	\N	/v6	2025-07-08 21:40:41.241441	\N	\N
26	127.0.0.1	curl/8.7.1	\N	/	2025-07-08 21:40:55.935191	\N	\N
27	127.0.0.1	curl/8.7.1	\N	/v6	2025-07-08 21:41:06.341969	\N	\N
28	127.0.0.1	curl/8.7.1	\N	/v6	2025-07-08 21:41:56.840731	\N	\N
29	127.0.0.1	curl/8.7.1	\N	/v6	2025-07-08 21:48:44.272291	\N	\N
30	127.0.0.1	curl/8.7.1	\N	/	2025-07-08 21:48:51.345989	\N	\N
31	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	\N	/v6	2025-07-08 21:49:22.424109	\N	\N
32	127.0.0.1	curl/8.7.1	\N	/v6	2025-07-08 21:59:16.407852	\N	\N
33	127.0.0.1	curl/8.7.1	\N	/	2025-07-08 21:59:22.860456	\N	\N
34	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	\N	/v6	2025-07-08 22:00:55.105338	\N	\N
35	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	\N	/	2025-07-08 22:01:42.525317	\N	\N
36	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	\N	/v6	2025-07-08 22:01:45.684973	\N	\N
37	127.0.0.1	curl/8.7.1	\N	/v6	2025-07-08 22:11:38.523592	\N	\N
38	127.0.0.1	curl/8.7.1	\N	/	2025-07-08 22:11:45.560566	\N	\N
39	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	\N	/	2025-07-08 22:14:07.40091	\N	\N
40	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	\N	/v6	2025-07-08 22:14:14.002938	\N	\N
41	127.0.0.1	curl/8.7.1	\N	/v6	2025-07-08 22:21:16.676558	\N	\N
42	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	\N	/v6	2025-07-08 22:32:46.502327	\N	\N
43	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	http://127.0.0.1:5001/v6	/assets/detail/20	2025-07-08 22:33:36.506463	\N	\N
44	127.0.0.1	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	\N	/	2025-07-08 22:33:48.653832	\N	\N
45	192.168.0.200	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	\N	/	2025-07-08 22:33:53.22225	\N	\N
46	192.168.0.200	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	\N	/v6	2025-07-08 22:33:58.8911	\N	\N
47	192.168.0.200	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36	\N	/	2025-07-08 22:34:34.930778	\N	\N
\.


--
-- Data for Name: onchain_history; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

COPY public.onchain_history (id, asset_id, trade_id, trigger_type, onchain_type, status, transaction_hash, block_number, gas_used, gas_price, error_message, retry_count, max_retries, triggered_by, triggered_at, processed_at, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: platform_incomes; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

COPY public.platform_incomes (id, type, amount, description, asset_id, related_id, tx_hash, created_at) FROM stdin;
1	2	0.002875	资产 2 交易手续费	2	4	mock_1741657622_Ev6fjJQR1p5rgWKQ8pH6Yu2tVSwLzQPp	2025-03-11 01:47:04.884068
2	2	0.002875	资产 2 交易手续费	2	5	mock_1741657683_gv92RGSj2UWdDkLQzFFE3Qo9qmaZetKA	2025-03-11 01:48:05.338805
3	2	0.002875	资产 2 交易手续费	2	6	mock_1741658983_ZADEqioxxGmLCTeP1r5mbf5KXzNiFH1z	2025-03-11 02:09:45.153279
4	2	0.014375	交易佣金 - 资产ID2, 交易ID55	2	55	\N	2025-03-12 16:20:51.221679
5	2	0.002875	交易佣金 - 资产ID2, 交易ID56	2	56	\N	2025-03-12 16:33:34.110181
6	2	0.00575	交易佣金 - 资产ID2, 交易ID57	2	57	\N	2025-03-12 16:33:51.261738
7	2	0.008625	交易佣金 - 资产ID2, 交易ID58	2	58	\N	2025-03-12 16:33:59.779962
8	2	0.0115	交易佣金 - 资产ID2, 交易ID59	2	59	\N	2025-03-12 16:34:05.786409
9	2	0.014375	交易佣金 - 资产ID2, 交易ID60	2	60	\N	2025-03-12 16:34:13.226798
10	2	0.01725	交易佣金 - 资产ID2, 交易ID61	2	61	\N	2025-03-12 16:37:20.65675
11	2	0.020125	交易佣金 - 资产ID2, 交易ID62	2	62	\N	2025-03-12 16:37:36.105763
12	2	0.002875	交易佣金 - 资产ID2, 交易ID63	2	63	\N	2025-03-12 23:57:20.999575
13	2	0.0115	交易佣金 - 资产ID2, 交易ID64	2	64	\N	2025-03-12 23:57:55.820254
14	2	0.014375	交易佣金 - 资产ID2, 交易ID65	2	65	\N	2025-03-13 00:51:09.337645
15	2	0.002875	交易佣金 - 资产ID2, 交易ID66	2	66	\N	2025-03-13 06:04:03.157314
16	2	0.00575	交易佣金 - 资产ID2, 交易ID67	2	67	\N	2025-03-13 06:04:11.711211
17	2	0.008625	交易佣金 - 资产ID2, 交易ID68	2	68	\N	2025-03-13 06:17:39.147821
18	2	0.002875	交易佣金 - 资产ID2, 交易ID70	2	70	\N	2025-03-13 08:04:19.726716
19	2	0.0115	交易佣金 - 资产ID2, 交易ID71	2	71	\N	2025-03-13 08:15:46.748165
20	2	0.008625	交易佣金 - 资产ID2, 交易ID72	2	72	\N	2025-03-13 08:16:05.027347
21	2	0.01725	交易佣金 - 资产ID2, 交易ID73	2	73	\N	2025-03-13 08:18:16.622401
22	2	0.002875	交易佣金 - 资产ID2, 交易ID74	2	74	\N	2025-03-13 12:39:53.716111
23	2	0.00575	交易佣金 - 资产ID2, 交易ID75	2	75	\N	2025-03-13 12:40:51.888779
24	2	0.008625	交易佣金 - 资产ID2, 交易ID76	2	76	\N	2025-03-13 12:50:44.502709
25	2	0.0115	交易佣金 - 资产ID2, 交易ID77	2	77	\N	2025-03-13 12:51:18.893752
26	2	0.014375	交易佣金 - 资产ID2, 交易ID78	2	78	\N	2025-03-13 12:58:11.093298
27	2	0.0115	交易佣金 - 资产ID2, 交易ID79	2	79	\N	2025-03-13 13:04:09.428773
28	2	0.008625	交易佣金 - 资产ID2, 交易ID80	2	80	\N	2025-03-13 13:14:15.425583
29	2	0.00575	交易佣金 - 资产ID2, 交易ID81	2	81	\N	2025-03-13 13:42:57.616721
30	2	0.002875	交易佣金 - 资产ID2, 交易ID82	2	82	\N	2025-03-13 13:43:15.120151
31	2	0.002875	交易佣金 - 资产ID2, 交易ID83	2	83	\N	2025-03-13 14:22:14.420887
32	2	0.002875	交易佣金 - 资产ID2, 交易ID84	2	84	\N	2025-03-13 14:51:24.043172
33	2	0.00575	交易佣金 - 资产ID2, 交易ID85	2	85	\N	2025-03-13 14:51:40.136172
34	2	0.002875	交易佣金 - 资产ID2, 交易ID86	2	86	\N	2025-03-13 15:17:55.02148
35	2	0.00575	交易佣金 - 资产ID2, 交易ID87	2	87	\N	2025-03-13 15:47:42.406197
36	2	0.02875	交易佣金 - 资产ID2, 交易ID88	2	88	\N	2025-03-13 16:03:48.594235
37	2	0.002875	交易佣金 - 资产ID2, 交易ID89	2	89	\N	2025-03-16 16:03:36.418639
38	2	0.020125	交易佣金 - 资产ID2, 交易ID91	2	91	\N	2025-03-16 18:57:09.36247
39	2	0.020125	交易佣金 - 资产ID2, 交易ID92	2	92	\N	2025-03-16 19:10:44.321134
40	2	0.04025	交易佣金 - 资产ID2, 交易ID93	2	93	\N	2025-03-16 19:11:14.10692
\.


--
-- Data for Name: share_messages; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

COPY public.share_messages (id, content, is_active, weight, created_at, updated_at) FROM stdin;
4	🚀 发现优质RWA资产！真实世界资产数字化投资新机遇，透明度高、收益稳定。通过我的专属链接投资，我们都能获得长期收益！	t	3	2025-05-30 21:17:45.90579	2025-05-30 21:17:45.905792
5	💎 区块链遇见传统资产！这个RWA项目通过区块链技术让实体资产投资更加透明安全。一起探索数字化投资的未来吧！	t	2	2025-05-30 21:17:45.905792	2025-05-30 21:17:45.905792
6	🌟 投资新趋势：真实世界资产代币化！房产、艺术品等实体资产现在可以通过区块链投资，门槛更低，流动性更强！	t	2	2025-05-30 21:17:45.905793	2025-05-30 21:17:45.905794
7	🔗 RWA投资社区邀请！真实世界资产代币化让投资更加透明、便捷。通过专属链接加入，共享投资智慧！	t	2	2025-05-30 21:17:45.905794	2025-05-30 21:17:45.905795
8	📊 传统投资的区块链革命！RWA（真实世界资产）让房产、商品等实体投资变得更加民主化。点击探索投资新世界！	t	1	2025-05-30 21:17:45.905795	2025-05-30 21:17:45.905795
\.


--
-- Data for Name: short_links; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

COPY public.short_links (id, code, original_url, created_at, expires_at, click_count, creator_address) FROM stdin;
1	QNoop2	http://example.com/asset/123	2025-03-17 06:24:30.090505	\N	0	0x123456789abcdef
2	cF73ND	http://127.0.0.1:9000/assets/RH-109774?ref=0x6260c4a9e9f725a9c40bede853240d311e80e9ee	2025-03-17 06:41:59.476325	2026-03-17 06:41:59.474951	0	0x6260c4a9e9f725a9c40bede853240d311e80e9ee
3	FI8Hkp	http://127.0.0.1:9000/assets/RH-109774?ref=0x6260c4a9e9f725a9c40bede853240d311e80e9ee	2025-03-17 06:42:45.180811	2026-03-17 06:42:45.180151	0	0x6260c4a9e9f725a9c40bede853240d311e80e9ee
4	AyzZs2	http://127.0.0.1:9000/assets/RH-109774?ref=0x6260c4a9e9f725a9c40bede853240d311e80e9ee	2025-03-17 06:49:16.536901	2026-03-17 06:49:16.536498	0	0x6260c4a9e9f725a9c40bede853240d311e80e9ee
5	MGMJB8	http://127.0.0.1:8000/assets/RH-109774?ref=0x6260c4a9e9f725a9c40bede853240d311e80e9ee	2025-03-17 06:50:41.510544	2026-03-17 06:50:41.508588	0	0x6260c4a9e9f725a9c40bede853240d311e80e9ee
6	mlM6wr	http://127.0.0.1:8000/assets/RH-109774?ref=0x6260c4a9e9f725a9c40bede853240d311e80e9ee	2025-03-17 06:50:50.030143	2026-03-17 06:50:50.029468	0	0x6260c4a9e9f725a9c40bede853240d311e80e9ee
7	axlOxn	http://127.0.0.1:8000/assets/RH-109774?ref=0x6260c4a9e9f725a9c40bede853240d311e80e9ee	2025-03-17 06:51:40.038977	2026-03-17 06:51:40.037886	0	0x6260c4a9e9f725a9c40bede853240d311e80e9ee
8	C3aKHK	http://127.0.0.1:8000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-17 07:52:48.923576	2026-03-17 07:52:48.922994	0	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR
9	y5wkyo	http://127.0.0.1:8000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-17 07:52:54.051964	2026-03-17 07:52:54.051158	0	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR
10	SABXp0	http://127.0.0.1:8000/assets/RH-109774?ref=0x6260c4a9e9f725a9c40bede853240d311e80e9ee	2025-03-17 07:54:21.918511	2026-03-17 07:54:21.91803	0	0x6260c4a9e9f725a9c40bede853240d311e80e9ee
11	zEtAAm	http://127.0.0.1:8000/assets/RH-109774?ref=0x6260c4a9e9f725a9c40bede853240d311e80e9ee	2025-03-17 08:59:48.230934	2026-03-17 08:59:48.230006	0	0x6260c4a9e9f725a9c40bede853240d311e80e9ee
12	zRZKBv	http://127.0.0.1:5000/assets/RH-109774?ref=0x6260c4a9e9f725a9c40bede853240d311e80e9ee	2025-03-17 12:23:26.605907	2026-03-17 12:23:26.603108	0	0x6260c4a9e9f725a9c40bede853240d311e80e9ee
13	jjOsAr	http://127.0.0.1:5000/assets/RH-109774?ref=0x6260c4a9e9f725a9c40bede853240d311e80e9ee	2025-03-17 12:55:03.505241	2026-03-17 12:55:03.503144	0	0x6260c4a9e9f725a9c40bede853240d311e80e9ee
14	aeQncd	http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-17 13:17:00.323135	2026-03-17 13:17:00.322322	0	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR
15	g8NTTP	http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-17 13:17:07.535723	2026-03-17 13:17:07.535252	0	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR
16	rHSfCW	http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-17 13:17:43.461365	2026-03-17 13:17:43.460505	0	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR
17	e1tBV3	http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-17 13:18:07.116898	2026-03-17 13:18:07.111747	0	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR
18	g3NUJw	http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-17 13:18:09.80652	2026-03-17 13:18:09.806026	0	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR
19	IzBEQo	http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-17 13:18:15.27811	2026-03-17 13:18:15.277587	0	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR
20	tkjDy2	http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-17 13:18:26.72366	2026-03-17 13:18:26.722978	0	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR
21	4xZT3r	http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-17 13:18:31.848799	2026-03-17 13:18:31.848298	0	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR
22	vpnBlK	http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-17 13:18:36.794353	2026-03-17 13:18:36.793878	0	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR
23	BA8hqE	http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-17 13:18:40.626197	2026-03-17 13:18:40.624863	0	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR
24	NCf8wF	http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-17 13:18:44.294044	2026-03-17 13:18:44.293567	0	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR
25	qn1OuI	http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-17 13:18:49.986129	2026-03-17 13:18:49.98318	0	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR
26	Ql6BC1	http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-17 13:18:52.385786	2026-03-17 13:18:52.385284	0	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR
27	ZX2NXg	http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-17 13:18:55.78561	2026-03-17 13:18:55.78526	0	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR
28	tVS5vm	http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-17 13:18:59.490261	2026-03-17 13:18:59.489907	0	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR
29	QhqU9g	http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-17 13:19:01.156524	2026-03-17 13:19:01.156116	0	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR
30	qZWU1A	http://127.0.0.1:5000/assets/RH-109774?ref=0x6260c4a9e9f725a9c40bede853240d311e80e9ee	2025-03-17 13:25:23.433814	2026-03-17 13:25:23.433328	0	0x6260c4a9e9f725a9c40bede853240d311e80e9ee
31	eh2gS5	http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-17 13:25:29.647967	2026-03-17 13:25:29.647577	0	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR
32	Jf8pSW	http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-17 13:25:36.355665	2026-03-17 13:25:36.355486	0	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR
33	Vjjk2p	http://127.0.0.1:9000/assets/RH-109774?ref=0xfe2b20231530e533552c5573582d6705b3ee9a1d	2025-03-17 13:28:09.786118	2026-03-17 13:28:09.779529	0	0xfe2b20231530e533552c5573582d6705b3ee9a1d
34	1raWnn	http://127.0.0.1:9000/assets/RH-109774?ref=0xfe2b20231530e533552c5573582d6705b3ee9a1d	2025-03-17 13:28:25.15073	2026-03-17 13:28:25.150071	0	0xfe2b20231530e533552c5573582d6705b3ee9a1d
35	Hxye3I	http://127.0.0.1:8000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-17 13:38:58.160239	2026-03-17 13:38:58.158204	0	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR
36	n7SfZh	http://127.0.0.1:8000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-17 13:43:40.535806	2026-03-17 13:43:40.535162	0	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR
37	SuCBql	http://127.0.0.1:8000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-17 13:44:28.836188	2026-03-17 13:44:28.835686	0	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR
38	UNS00i	http://127.0.0.1:8000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-17 13:44:55.242824	2026-03-17 13:44:55.241473	0	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR
39	ig1ucf	http://127.0.0.1:8000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-17 14:43:09.82465	2026-03-17 14:43:09.823885	0	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR
40	VxcS9c	http://127.0.0.1:8000/assets/RH-109774?ref=0x6260c4a9e9f725a9c40bede853240d311e80e9ee	2025-03-17 15:32:08.32396	2026-03-17 15:32:08.319996	0	0x6260c4a9e9f725a9c40bede853240d311e80e9ee
41	8Fy9Xa	http://127.0.0.1:8000/assets/RH-109774?ref=0x6260c4a9e9f725a9c40bede853240d311e80e9ee	2025-03-17 15:32:34.967009	2026-03-17 15:32:34.966412	0	0x6260c4a9e9f725a9c40bede853240d311e80e9ee
42	6eHJzU	http://127.0.0.1:8000/assets/RH-109774?ref=0x6260c4a9e9f725a9c40bede853240d311e80e9ee	2025-03-17 15:32:38.595202	2026-03-17 15:32:38.594663	0	0x6260c4a9e9f725a9c40bede853240d311e80e9ee
43	9CT1By	http://127.0.0.1:8000/assets/RH-109774?ref=0x6260c4a9e9f725a9c40bede853240d311e80e9ee	2025-03-17 16:05:19.425427	2026-03-17 16:05:19.424937	0	0x6260c4a9e9f725a9c40bede853240d311e80e9ee
44	MGksHt	http://127.0.0.1:8000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-17 17:21:48.885438	2026-03-17 17:21:48.884615	0	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR
45	xHPVtO	http://127.0.0.1:8000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-18 10:01:07.162402	2026-03-18 10:01:07.160722	0	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR
46	NO75rL	http://127.0.0.1:8000/assets/10?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-18 13:52:00.477426	2026-03-18 13:52:00.476493	0	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR
47	R4eBON	http://127.0.0.1:8000/assets/10?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-18 14:41:32.943737	2026-03-18 14:41:32.94204	0	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR
48	lfiylC	http://127.0.0.1:8000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-18 17:33:43.104652	2026-03-18 17:33:43.102782	0	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR
49	yAmXTJ	http://127.0.0.1:8000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-18 18:58:50.935444	2026-03-18 18:58:50.93441	0	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR
50	x0olqD	http://127.0.0.1:8000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-19 06:47:27.956059	2026-03-19 06:47:27.953377	0	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR
51	RE6Kd9	http://127.0.0.1:8000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-19 06:49:22.379527	2026-03-19 06:49:22.378969	0	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR
52	Y6yONO	http://127.0.0.1:8000/assets/RH-101719?ref=0x6394993426DBA3b654eF0052698Fe9E0B6A98870	2025-03-19 10:50:40.19337	2026-03-19 10:50:40.191664	0	0x6394993426DBA3b654eF0052698Fe9E0B6A98870
53	CFnJ5y	https://example.com	2025-05-30 21:08:40.188464	2026-05-30 21:08:40.188185	0	\N
\.


--
-- Data for Name: system_configs; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

COPY public.system_configs (id, config_key, config_value, description, created_at, updated_at) FROM stdin;
1	PLATFORM_FEE_ADDRESS	EsfAFJFBa49RMc2UZNUjsWhGFZeA1uLgEkNPY5oYsDW4	Platform fee collection address	2025-05-26 09:05:46.150915	2025-05-26 09:05:46.150916
2	ASSET_CREATION_FEE_ADDRESS	EsfAFJFBa49RMc2UZNUjsWhGFZeA1uLgEkNPY5oYsDW4	Asset creation fee collection address	2025-05-26 09:05:46.157009	2025-05-26 09:05:46.157011
3	ASSET_CREATION_FEE_AMOUNT	0.02	Asset creation fee amount in USDC	2025-05-26 09:05:46.158027	2025-05-26 09:05:46.158028
4	PLATFORM_FEE_BASIS_POINTS	350	Platform fee in basis points (350 = 3.5%)	2025-05-26 09:05:46.158908	2025-05-26 09:05:46.158909
5	SOLANA_WALLET_ADDRESS	6UrwhN2rqQvo2tBfc9FZCdUbt9JLs3BJiEm7pv4NM41b	新的安全钱包地址	2025-05-27 06:39:28.015536	2025-05-27 06:39:28.015537
\.


--
-- Data for Name: trades; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

COPY public.trades (id, asset_id, type, amount, price, trader_address, created_at, is_self_trade, tx_hash, status, gas_used, total, fee, fee_rate, token_amount, payment_details) FROM stdin;
81	2	buy	2	0.575	eeyfrdpgtdtm9pldrxfq39c2skyd9sqkijw7keukjtlr	2025-03-13 13:42:54.571454	f	mock_1741873377587_meg1z3q4pah	completed	\N	1.15	0.00575	0.005	\N	\N
83	2	buy	1	0.575	eeyfrdpgtdtm9pldrxfq39c2skyd9sqkijw7keukjtlr	2025-03-13 14:22:11.378808	f	mock_1741875734395_274gopvsc9b	completed	\N	0.575	0.002875	0.005	\N	\N
85	2	buy	2	0.575	eeyfrdpgtdtm9pldrxfq39c2skyd9sqkijw7keukjtlr	2025-03-13 14:51:37.111535	f	mock_1741877500120_xg4mpvol79f	completed	\N	1.15	0.00575	0.005	\N	\N
88	2	buy	10	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-13 16:03:45.554951	f	mock_1741881828613_yi9wr3s5dj8	completed	\N	5.75	0.02875	0.005	\N	\N
91	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-16 18:57:06.311674	f	mock_1742151429340_8xc2al7pwzc	completed	\N	0.575	0.020125	0.035	\N	\N
92	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-16 19:10:41.293602	f	mock_1742152244304_7n6uib122xa	completed	\N	0.575	0.020125	0.035	\N	\N
96	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-16 20:00:37.814415	f	mock_1742155240823_seyzt0arscb	completed	\N	0.575	0.020125	0.035	\N	\N
99	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-16 20:03:56.997103	f	mock_1742155440012_6o9dxppcgf2	completed	\N	0.575	0.020125	0.035	\N	\N
102	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-16 20:06:47.678122	f	mock_1742155610693_mtz9exf1dq	completed	\N	0.575	0.020125	0.035	\N	\N
105	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-17 06:01:06.692257	f	\N	pending	\N	0.575	0.020125	0.035	\N	\N
108	10	buy	3	0.100011	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-18 16:07:08.185451	t	\N	pending	\N	0.300033	0.000300033	0.001	\N	\N
111	2	buy	100	0.575	0x6394993426dba3b654ef0052698fe9e0b6a98870	2025-03-19 12:47:21.129065	t	\N	pending	\N	57.49999999999999	0.057499999999999996	0.001	\N	\N
2	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 01:34:01.912501	f	\N	pending	\N	\N	\N	\N	\N	\N
3	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 01:36:39.563303	f	\N	pending	\N	\N	\N	\N	\N	\N
82	2	buy	1	0.575	eeyfrdpgtdtm9pldrxfq39c2skyd9sqkijw7keukjtlr	2025-03-13 13:43:12.085989	f	mock_1741873395101_gpn7i9gmvb7	completed	\N	0.575	0.002875	0.005	\N	\N
86	2	buy	1	0.575	eeyfrdpgtdtm9pldrxfq39c2skyd9sqkijw7keukjtlr	2025-03-13 15:17:51.986367	f	mock_1741879074996_llicbmr5wd	completed	\N	0.575	0.002875	0.005	\N	\N
89	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-16 16:03:33.387021	f	mock_1742141016404_s5ddqxtbcdb	completed	\N	0.575	0.002875	0.005	\N	\N
94	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-16 19:57:29.73411	f	\N	pending	\N	0.575	0.020125	0.035	\N	\N
97	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-16 20:01:53.023494	f	mock_1742155316032_wectcakdo7f	completed	\N	0.575	0.020125	0.035	\N	\N
100	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-16 20:05:36.946576	f	mock_1742155539964_b2hnh0fhjmd	completed	\N	0.575	0.020125	0.035	\N	\N
103	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-16 20:08:30.609813	f	mock_1742155713627_cvn2vw5ye3v	completed	\N	0.575	0.020125	0.035	\N	\N
106	2	buy	2	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-17 06:06:33.21776	f	\N	pending	\N	1.15	0.04025	0.035	\N	\N
109	2	buy	11	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-18 18:58:40.766895	f	\N	pending	\N	6.324999999999999	0.221375	0.035	\N	\N
112	13	buy	100	0.001002	HnPZkg9FpHjovNNZ8Au1MyLjYPbW9KsK87ACPCh1SvSd	2025-03-21 03:37:17.584328	f	\N	pending	\N	0.10020000000000001	0.0035070000000000006	0.035	\N	\N
113	14	buy	100	9.2e-05	8cU6PAtRTRgfyJu48qfz2hQP5aMGwooxqrCZtyB6UcYP	2025-03-21 14:10:19.289388	f	\N	pending	\N	0.0092	0.000322	0.035	\N	\N
8	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 07:57:26.79552	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
9	2	buy	2	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 07:57:40.356791	f	\N	pending	\N	1.15	0.00575	0.005	\N	\N
10	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 08:02:57.968949	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
11	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 08:35:31.387406	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
4	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 01:47:02.806353	f	mock_1741657622_Ev6fjJQR1p5rgWKQ8pH6Yu2tVSwLzQPp	completed	452470.0	\N	\N	\N	\N	\N
5	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 01:48:03.318717	f	mock_1741657683_gv92RGSj2UWdDkLQzFFE3Qo9qmaZetKA	completed	223715.0	\N	\N	\N	\N	\N
6	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 02:09:43.12098	f	mock_1741658983_ZADEqioxxGmLCTeP1r5mbf5KXzNiFH1z	completed	324145.0	\N	\N	\N	\N	\N
7	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 07:10:42.263731	f	mock_1741677042_wt6zh7Cz2w1QvZxeDAD8pqmFcBpu6zGZ	completed	392463	0.575	0.002875	0.005	\N	\N
12	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 08:35:43.357544	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
13	2	buy	4	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 08:36:01.968023	f	\N	pending	\N	2.3	0.0115	0.005	\N	\N
14	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 08:50:56.950477	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
15	2	buy	100	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 08:51:07.604542	f	\N	pending	\N	57.49999999999999	0.2875	0.005	\N	\N
16	2	buy	2322	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 08:53:30.971523	f	\N	pending	\N	1335.1499999999999	6.67575	0.005	\N	\N
17	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 09:21:08.318927	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
18	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 09:31:43.58982	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
19	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 10:26:46.290785	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
20	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 14:06:07.411956	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
21	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 15:00:01.475815	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
22	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 15:08:54.360278	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
23	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 15:09:45.746155	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
24	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 15:10:00.126374	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
25	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 15:54:51.347659	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
26	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 16:05:13.447889	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
27	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 16:07:18.830289	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
28	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 16:21:54.655306	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
29	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 16:22:02.972352	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
30	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 16:22:17.006642	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
31	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 16:29:21.065746	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
32	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 16:29:29.763004	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
33	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 16:34:15.795374	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
34	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 16:34:24.14688	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
35	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 16:34:38.989301	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
36	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-11 16:35:47.748019	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
37	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-12 05:07:06.337584	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
38	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-12 05:07:25.012396	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
39	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-12 05:22:18.71087	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
40	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-12 05:22:27.444989	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
41	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-12 05:27:52.184741	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
42	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-12 05:28:01.760034	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
43	2	buy	190	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-12 05:28:11.006242	f	\N	pending	\N	109.24999999999999	0.5462499999999999	0.005	\N	\N
44	2	buy	134	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-12 05:28:49.908681	f	\N	pending	\N	77.05	0.38525	0.005	\N	\N
45	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-12 09:10:54.742154	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
46	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-12 09:11:02.053127	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
47	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-12 09:11:11.215304	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
48	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-12 09:21:22.613331	f	mock_1741771285626_j6zg9afa5so	completed	\N	0.575	0.002875	0.005	\N	\N
49	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-12 09:21:30.362901	f	mock_1741771293372_y0pqzwz5p6	completed	\N	0.575	0.002875	0.005	\N	\N
50	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-12 09:21:44.404794	f	mock_1741771307416_i3ihxih8cgi	completed	\N	0.575	0.002875	0.005	\N	\N
51	2	buy	2	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-12 09:22:20.829135	f	mock_1741771343838_ujh9verq9qr	completed	\N	1.15	0.00575	0.005	\N	\N
52	2	buy	3	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-12 15:06:22.874899	f	mock_1741791985889_ixcrhz176gk	completed	\N	1.7249999999999999	0.008624999999999999	0.005	\N	\N
53	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-12 16:11:48.72489	f	\N	pending	\N	0.575	0.002875	0.005	\N	\N
54	2	buy	2	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-12 16:12:10.851048	f	\N	pending	\N	1.15	0.00575	0.005	\N	\N
55	2	buy	5	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-12 16:20:48.179399	f	mock_1741796451191_ly3o5sxubdi	completed	\N	2.875	0.014375	0.005	\N	\N
56	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-12 16:33:31.067868	f	mock_1741797214081_krj6qbda6y8	completed	\N	0.575	0.002875	0.005	\N	\N
57	2	buy	2	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-12 16:33:48.22228	f	mock_1741797231236_22ac66bsewv	completed	\N	1.15	0.00575	0.005	\N	\N
58	2	buy	3	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-12 16:33:56.759014	f	mock_1741797239765_h8hggr1kw1n	completed	\N	1.7249999999999999	0.008624999999999999	0.005	\N	\N
59	2	buy	4	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-12 16:34:02.741964	f	mock_1741797245762_uuhizajmno	completed	\N	2.3	0.0115	0.005	\N	\N
60	2	buy	5	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-12 16:34:10.199932	f	\N	completed	\N	2.875	0.014375	0.005	\N	\N
61	2	buy	6	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-12 16:37:17.549442	f	mock_1741797440587_z3rcix96n4h	completed	\N	3.4499999999999997	0.017249999999999998	0.005	\N	\N
62	2	buy	7	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-12 16:37:33.069605	f	mock_1741797456086_8ak9j7aevl5	completed	\N	4.0249999999999995	0.020124999999999997	0.005	\N	\N
63	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-12 23:57:17.945374	f	mock_1741823840964_wbylppgor3s	completed	\N	0.575	0.002875	0.005	\N	\N
64	2	buy	4	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-12 23:57:52.778012	f	mock_1741823875795_zrix662ayc	completed	\N	2.3	0.0115	0.005	\N	\N
65	2	buy	5	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-13 00:51:06.290646	f	mock_1741827069304_jpp8c8actg	completed	\N	2.875	0.014375	0.005	\N	\N
66	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-13 06:04:00.109373	f	mock_1741845843127_6avprjp4iqh	completed	\N	0.575	0.002875	0.005	\N	\N
67	2	buy	2	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-13 06:04:08.681488	f	mock_1741845851695_gw43q1lld7q	completed	\N	1.15	0.00575	0.005	\N	\N
68	2	buy	3	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-13 06:17:36.106661	f	mock_1741846659117_4pr3pj0wybb	completed	\N	1.7249999999999999	0.008624999999999999	0.005	\N	\N
69	2	buy	2	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-13 07:36:26.768457	f	\N	pending	\N	1.15	0.00575	0.005	\N	\N
70	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-13 08:04:16.689091	f	mock_1741853059702_9pxsrpjvnn9	completed	\N	0.575	0.002875	0.005	\N	\N
71	2	buy	4	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-13 08:15:43.69141	f	mock_1741853746720_kmiqg76lrdr	completed	\N	2.3	0.0115	0.005	\N	\N
72	2	buy	3	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-13 08:16:01.990233	f	mock_1741853765007_ip0fdjm297h	completed	\N	1.7249999999999999	0.008624999999999999	0.005	\N	\N
73	2	buy	6	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-13 08:18:13.601985	f	mock_1741853896612_p4bwgb0113	completed	\N	3.4499999999999997	0.017249999999999998	0.005	\N	\N
74	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-13 12:39:50.693203	f	mock_1741869593705_r3htny9df1s	completed	\N	0.575	0.002875	0.005	\N	\N
75	2	buy	2	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-13 12:40:48.870357	f	mock_1741869651878_93davb2nvhv	completed	\N	1.15	0.00575	0.005	\N	\N
76	2	buy	3	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-13 12:50:41.462234	f	mock_1741870244475_sfw3yn6lkqf	completed	\N	1.7249999999999999	0.008624999999999999	0.005	\N	\N
77	2	buy	4	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-13 12:51:15.858631	f	mock_1741870278871_omost1uw7j	completed	\N	2.3	0.0115	0.005	\N	\N
78	2	buy	5	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-13 12:58:08.059793	f	mock_1741870691071_ftztmhjkbk8	completed	\N	2.875	0.014375	0.005	\N	\N
79	2	buy	4	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-13 13:04:06.40009	f	mock_1741871049414_iezmrcajkcc	completed	\N	2.3	0.0115	0.005	\N	\N
80	2	buy	3	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-13 13:14:12.391221	f	mock_1741871655409_n2lmjxeva7k	completed	\N	1.7249999999999999	0.008624999999999999	0.005	\N	\N
84	2	buy	1	0.575	eeyfrdpgtdtm9pldrxfq39c2skyd9sqkijw7keukjtlr	2025-03-13 14:51:21.02022	f	mock_1741877484032_87uyuywc6wx	completed	\N	0.575	0.002875	0.005	\N	\N
87	2	buy	2	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-13 15:47:39.363903	f	mock_1741880862381_ijvy8k2tdcp	completed	\N	1.15	0.00575	0.005	\N	\N
90	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-16 18:55:37.451394	f	\N	failed	\N	0.575	0.020125	0.035	\N	\N
93	2	buy	2	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-16 19:11:11.069502	f	mock_1742152274090_m2qk7gd81v	completed	\N	1.15	0.04025	0.035	\N	\N
95	2	buy	3	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-16 19:58:50.397324	f	\N	pending	\N	1.7249999999999999	0.060375	0.035	\N	\N
98	2	buy	1	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-16 20:03:03.029528	f	mock_1742155386041_4pq7v16fz3	completed	\N	0.575	0.020125	0.035	\N	\N
101	2	buy	2	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-16 20:06:02.04203	f	mock_1742155565062_9rseqmmgrj5	completed	\N	1.15	0.04025	0.035	\N	\N
104	2	buy	2	0.575	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-16 20:18:01.499463	f	mock_1742156284521_3p8lsoz7red	completed	\N	1.15	0.04025	0.035	\N	\N
107	10	buy	100	0.100011	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-18 16:04:36.785898	t	\N	pending	\N	10.001100000000001	0.0100011	0.001	\N	\N
110	11	buy	100	1.000106	EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR	2025-03-19 00:32:03.570541	t	\N	pending	\N	100.0106	0.1000106	0.001	\N	\N
114	14	buy	140	9.2e-05	8cU6PAtRTRgfyJu48qfz2hQP5aMGwooxqrCZtyB6UcYP	2025-03-21 14:12:21.033078	f	\N	pending	\N	0.01288	0.00045080000000000006	0.035	\N	\N
\.


--
-- Data for Name: transactions; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

COPY public.transactions (id, from_address, to_address, amount, token_symbol, signature, status, tx_type, data, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: user_commission_balance; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

COPY public.user_commission_balance (id, user_address, total_earned, available_balance, withdrawn_amount, frozen_amount, currency, last_updated, created_at) FROM stdin;
2	0x1234567890123456789012345678901234567890	301.50000000	201.00000000	0.00000000	100.50000000	USDC	2025-05-26 16:14:14.602921	2025-05-26 16:10:52.159178
3	0xtest123456789012345678901234567890	150.00000000	60.00000000	30.00000000	60.00000000	USDC	2025-05-26 16:14:14.749053	2025-05-26 16:10:52.307403
\.


--
-- Data for Name: user_referrals; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

COPY public.user_referrals (id, user_address, referrer_address, referral_level, referral_code, joined_at, created_at, referral_time, asset_id, status) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

COPY public.users (id, username, email, password_hash, eth_address, nonce, role, status, settings, is_active, last_login_at, created_at, updated_at, solana_address, wallet_type, is_distributor, is_verified, is_blocked, referrer_address) FROM stdin;
\.


--
-- Data for Name: withdrawal_requests; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

COPY public.withdrawal_requests (id, user_address, amount, type, status, transaction_hash, created_at, updated_at) FROM stdin;
\.


--
-- Name: admin_operation_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rwa_hub_user
--

SELECT pg_catalog.setval('public.admin_operation_logs_id_seq', 2, true);


--
-- Name: admin_users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rwa_hub_user
--

SELECT pg_catalog.setval('public.admin_users_id_seq', 2, true);


--
-- Name: asset_status_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rwa_hub_user
--

SELECT pg_catalog.setval('public.asset_status_history_id_seq', 1, false);


--
-- Name: assets_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rwa_hub_user
--

SELECT pg_catalog.setval('public.assets_id_seq', 21, false);


--
-- Name: commission_config_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rwa_hub_user
--

SELECT pg_catalog.setval('public.commission_config_id_seq', 4, true);


--
-- Name: commission_records_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rwa_hub_user
--

SELECT pg_catalog.setval('public.commission_records_id_seq', 24, true);


--
-- Name: commission_settings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rwa_hub_user
--

SELECT pg_catalog.setval('public.commission_settings_id_seq', 3, true);


--
-- Name: commission_withdrawals_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rwa_hub_user
--

SELECT pg_catalog.setval('public.commission_withdrawals_id_seq', 8, true);


--
-- Name: commissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rwa_hub_user
--

SELECT pg_catalog.setval('public.commissions_id_seq', 1, false);


--
-- Name: dashboard_stats_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rwa_hub_user
--

SELECT pg_catalog.setval('public.dashboard_stats_id_seq', 37, true);


--
-- Name: distribution_levels_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rwa_hub_user
--

SELECT pg_catalog.setval('public.distribution_levels_id_seq', 3, true);


--
-- Name: distribution_settings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rwa_hub_user
--

SELECT pg_catalog.setval('public.distribution_settings_id_seq', 3, true);


--
-- Name: dividend_distributions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rwa_hub_user
--

SELECT pg_catalog.setval('public.dividend_distributions_id_seq', 1, false);


--
-- Name: dividend_records_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rwa_hub_user
--

SELECT pg_catalog.setval('public.dividend_records_id_seq', 1, false);


--
-- Name: dividends_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rwa_hub_user
--

SELECT pg_catalog.setval('public.dividends_id_seq', 1, false);


--
-- Name: holdings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rwa_hub_user
--

SELECT pg_catalog.setval('public.holdings_id_seq', 1, false);


--
-- Name: ip_visits_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rwa_hub_user
--

SELECT pg_catalog.setval('public.ip_visits_id_seq', 47, true);


--
-- Name: onchain_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rwa_hub_user
--

SELECT pg_catalog.setval('public.onchain_history_id_seq', 1, false);


--
-- Name: platform_incomes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rwa_hub_user
--

SELECT pg_catalog.setval('public.platform_incomes_id_seq', 40, true);


--
-- Name: share_messages_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rwa_hub_user
--

SELECT pg_catalog.setval('public.share_messages_id_seq', 8, true);


--
-- Name: short_links_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rwa_hub_user
--

SELECT pg_catalog.setval('public.short_links_id_seq', 53, true);


--
-- Name: system_configs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rwa_hub_user
--

SELECT pg_catalog.setval('public.system_configs_id_seq', 6, true);


--
-- Name: trades_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rwa_hub_user
--

SELECT pg_catalog.setval('public.trades_id_seq', 115, true);


--
-- Name: transactions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rwa_hub_user
--

SELECT pg_catalog.setval('public.transactions_id_seq', 1, false);


--
-- Name: user_commission_balance_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rwa_hub_user
--

SELECT pg_catalog.setval('public.user_commission_balance_id_seq', 3, true);


--
-- Name: user_referrals_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rwa_hub_user
--

SELECT pg_catalog.setval('public.user_referrals_id_seq', 1, false);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rwa_hub_user
--

SELECT pg_catalog.setval('public.users_id_seq', 1, false);


--
-- Name: withdrawal_requests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: rwa_hub_user
--

SELECT pg_catalog.setval('public.withdrawal_requests_id_seq', 1, false);


--
-- Name: admin_operation_logs admin_operation_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.admin_operation_logs
    ADD CONSTRAINT admin_operation_logs_pkey PRIMARY KEY (id);


--
-- Name: admin_users admin_users_pkey; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.admin_users
    ADD CONSTRAINT admin_users_pkey PRIMARY KEY (id);


--
-- Name: admin_users admin_users_wallet_address_key; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.admin_users
    ADD CONSTRAINT admin_users_wallet_address_key UNIQUE (wallet_address);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: asset_status_history asset_status_history_pkey; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.asset_status_history
    ADD CONSTRAINT asset_status_history_pkey PRIMARY KEY (id);


--
-- Name: assets assets_pkey; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.assets
    ADD CONSTRAINT assets_pkey PRIMARY KEY (id);


--
-- Name: assets assets_token_address_key; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.assets
    ADD CONSTRAINT assets_token_address_key UNIQUE (token_address);


--
-- Name: assets assets_token_symbol_key; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.assets
    ADD CONSTRAINT assets_token_symbol_key UNIQUE (token_symbol);


--
-- Name: commission_config commission_config_config_key_key; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.commission_config
    ADD CONSTRAINT commission_config_config_key_key UNIQUE (config_key);


--
-- Name: commission_config commission_config_pkey; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.commission_config
    ADD CONSTRAINT commission_config_pkey PRIMARY KEY (id);


--
-- Name: commission_records commission_records_pkey; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.commission_records
    ADD CONSTRAINT commission_records_pkey PRIMARY KEY (id);


--
-- Name: commission_settings commission_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.commission_settings
    ADD CONSTRAINT commission_settings_pkey PRIMARY KEY (id);


--
-- Name: commission_withdrawals commission_withdrawals_pkey; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.commission_withdrawals
    ADD CONSTRAINT commission_withdrawals_pkey PRIMARY KEY (id);


--
-- Name: commissions commissions_pkey; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.commissions
    ADD CONSTRAINT commissions_pkey PRIMARY KEY (id);


--
-- Name: dashboard_stats dashboard_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.dashboard_stats
    ADD CONSTRAINT dashboard_stats_pkey PRIMARY KEY (id);


--
-- Name: distribution_levels distribution_levels_level_key; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.distribution_levels
    ADD CONSTRAINT distribution_levels_level_key UNIQUE (level);


--
-- Name: distribution_levels distribution_levels_pkey; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.distribution_levels
    ADD CONSTRAINT distribution_levels_pkey PRIMARY KEY (id);


--
-- Name: distribution_settings distribution_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.distribution_settings
    ADD CONSTRAINT distribution_settings_pkey PRIMARY KEY (id);


--
-- Name: dividend_distributions dividend_distributions_pkey; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.dividend_distributions
    ADD CONSTRAINT dividend_distributions_pkey PRIMARY KEY (id);


--
-- Name: dividend_records dividend_records_pkey; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.dividend_records
    ADD CONSTRAINT dividend_records_pkey PRIMARY KEY (id);


--
-- Name: dividends dividends_pkey; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.dividends
    ADD CONSTRAINT dividends_pkey PRIMARY KEY (id);


--
-- Name: holdings holdings_pkey; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.holdings
    ADD CONSTRAINT holdings_pkey PRIMARY KEY (id);


--
-- Name: ip_visits ip_visits_pkey; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.ip_visits
    ADD CONSTRAINT ip_visits_pkey PRIMARY KEY (id);


--
-- Name: onchain_history onchain_history_pkey; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.onchain_history
    ADD CONSTRAINT onchain_history_pkey PRIMARY KEY (id);


--
-- Name: platform_incomes platform_incomes_pkey; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.platform_incomes
    ADD CONSTRAINT platform_incomes_pkey PRIMARY KEY (id);


--
-- Name: share_messages share_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.share_messages
    ADD CONSTRAINT share_messages_pkey PRIMARY KEY (id);


--
-- Name: short_links short_links_pkey; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.short_links
    ADD CONSTRAINT short_links_pkey PRIMARY KEY (id);


--
-- Name: system_configs system_configs_config_key_key; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.system_configs
    ADD CONSTRAINT system_configs_config_key_key UNIQUE (config_key);


--
-- Name: system_configs system_configs_pkey; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.system_configs
    ADD CONSTRAINT system_configs_pkey PRIMARY KEY (id);


--
-- Name: trades trades_pkey; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.trades
    ADD CONSTRAINT trades_pkey PRIMARY KEY (id);


--
-- Name: transactions transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_pkey PRIMARY KEY (id);


--
-- Name: transactions transactions_signature_key; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_signature_key UNIQUE (signature);


--
-- Name: holdings uix_user_asset; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.holdings
    ADD CONSTRAINT uix_user_asset UNIQUE (user_id, asset_id);


--
-- Name: user_commission_balance user_commission_balance_pkey; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.user_commission_balance
    ADD CONSTRAINT user_commission_balance_pkey PRIMARY KEY (id);


--
-- Name: user_commission_balance user_commission_balance_user_address_key; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.user_commission_balance
    ADD CONSTRAINT user_commission_balance_user_address_key UNIQUE (user_address);


--
-- Name: user_referrals user_referrals_pkey; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.user_referrals
    ADD CONSTRAINT user_referrals_pkey PRIMARY KEY (id);


--
-- Name: user_referrals user_referrals_user_address_key; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.user_referrals
    ADD CONSTRAINT user_referrals_user_address_key UNIQUE (user_address);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_eth_address_key; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_eth_address_key UNIQUE (eth_address);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_solana_address_key; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_solana_address_key UNIQUE (solana_address);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: withdrawal_requests withdrawal_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.withdrawal_requests
    ADD CONSTRAINT withdrawal_requests_pkey PRIMARY KEY (id);


--
-- Name: idx_active_holdings; Type: INDEX; Schema: public; Owner: rwa_hub_user
--

CREATE INDEX idx_active_holdings ON public.holdings USING btree (user_id, quantity);


--
-- Name: idx_asset_holders; Type: INDEX; Schema: public; Owner: rwa_hub_user
--

CREATE INDEX idx_asset_holders ON public.holdings USING btree (asset_id);


--
-- Name: idx_ip_timestamp; Type: INDEX; Schema: public; Owner: rwa_hub_user
--

CREATE INDEX idx_ip_timestamp ON public.ip_visits USING btree (ip_address, "timestamp");


--
-- Name: idx_timestamp_desc; Type: INDEX; Schema: public; Owner: rwa_hub_user
--

CREATE INDEX idx_timestamp_desc ON public.ip_visits USING btree ("timestamp");


--
-- Name: idx_user_holdings; Type: INDEX; Schema: public; Owner: rwa_hub_user
--

CREATE INDEX idx_user_holdings ON public.holdings USING btree (user_id);


--
-- Name: ix_assets_asset_type; Type: INDEX; Schema: public; Owner: rwa_hub_user
--

CREATE INDEX ix_assets_asset_type ON public.assets USING btree (asset_type);


--
-- Name: ix_assets_created_at; Type: INDEX; Schema: public; Owner: rwa_hub_user
--

CREATE INDEX ix_assets_created_at ON public.assets USING btree (created_at);


--
-- Name: ix_assets_location; Type: INDEX; Schema: public; Owner: rwa_hub_user
--

CREATE INDEX ix_assets_location ON public.assets USING btree (location);


--
-- Name: ix_assets_name; Type: INDEX; Schema: public; Owner: rwa_hub_user
--

CREATE INDEX ix_assets_name ON public.assets USING btree (name);


--
-- Name: ix_assets_status; Type: INDEX; Schema: public; Owner: rwa_hub_user
--

CREATE INDEX ix_assets_status ON public.assets USING btree (status);


--
-- Name: ix_commission_withdrawals_user_address; Type: INDEX; Schema: public; Owner: rwa_hub_user
--

CREATE INDEX ix_commission_withdrawals_user_address ON public.commission_withdrawals USING btree (user_address);


--
-- Name: ix_ip_visits_ip_address; Type: INDEX; Schema: public; Owner: rwa_hub_user
--

CREATE INDEX ix_ip_visits_ip_address ON public.ip_visits USING btree (ip_address);


--
-- Name: ix_ip_visits_timestamp; Type: INDEX; Schema: public; Owner: rwa_hub_user
--

CREATE INDEX ix_ip_visits_timestamp ON public.ip_visits USING btree ("timestamp");


--
-- Name: ix_short_links_code; Type: INDEX; Schema: public; Owner: rwa_hub_user
--

CREATE UNIQUE INDEX ix_short_links_code ON public.short_links USING btree (code);


--
-- Name: ix_transactions_from_address; Type: INDEX; Schema: public; Owner: rwa_hub_user
--

CREATE INDEX ix_transactions_from_address ON public.transactions USING btree (from_address);


--
-- Name: ix_transactions_to_address; Type: INDEX; Schema: public; Owner: rwa_hub_user
--

CREATE INDEX ix_transactions_to_address ON public.transactions USING btree (to_address);


--
-- Name: assets assets_sequence_check; Type: TRIGGER; Schema: public; Owner: rwa_hub_user
--

CREATE TRIGGER assets_sequence_check BEFORE INSERT ON public.assets FOR EACH ROW EXECUTE FUNCTION public.check_assets_sequence();


--
-- Name: asset_status_history asset_status_history_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.asset_status_history
    ADD CONSTRAINT asset_status_history_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id);


--
-- Name: commission_records commission_records_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.commission_records
    ADD CONSTRAINT commission_records_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id);


--
-- Name: commission_records commission_records_transaction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.commission_records
    ADD CONSTRAINT commission_records_transaction_id_fkey FOREIGN KEY (transaction_id) REFERENCES public.trades(id);


--
-- Name: dividend_distributions dividend_distributions_dividend_record_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.dividend_distributions
    ADD CONSTRAINT dividend_distributions_dividend_record_id_fkey FOREIGN KEY (dividend_record_id) REFERENCES public.dividend_records(id);


--
-- Name: dividend_records dividend_records_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.dividend_records
    ADD CONSTRAINT dividend_records_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id);


--
-- Name: dividends dividends_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.dividends
    ADD CONSTRAINT dividends_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id);


--
-- Name: holdings holdings_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.holdings
    ADD CONSTRAINT holdings_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id);


--
-- Name: holdings holdings_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.holdings
    ADD CONSTRAINT holdings_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: onchain_history onchain_history_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.onchain_history
    ADD CONSTRAINT onchain_history_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id);


--
-- Name: onchain_history onchain_history_trade_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.onchain_history
    ADD CONSTRAINT onchain_history_trade_id_fkey FOREIGN KEY (trade_id) REFERENCES public.trades(id);


--
-- Name: platform_incomes platform_incomes_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.platform_incomes
    ADD CONSTRAINT platform_incomes_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id);


--
-- Name: trades trades_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.trades
    ADD CONSTRAINT trades_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id);


--
-- Name: user_referrals user_referrals_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: rwa_hub_user
--

ALTER TABLE ONLY public.user_referrals
    ADD CONSTRAINT user_referrals_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id);


--
-- PostgreSQL database dump complete
--

