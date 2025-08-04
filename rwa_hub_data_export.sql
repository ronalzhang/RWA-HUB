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

--
-- Data for Name: admin_operation_logs; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

INSERT INTO public.admin_operation_logs VALUES (1, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '更新分销等级', 'level', '2', '{"method": "PUT", "url": "/api/admin/v2/distribution-levels/2", "args": {}, "body": {"level": 2, "commission_rate": 15, "description": "\u4e8c\u7ea7\u5206\u9500", "is_active": true}, "status_code": 200}', '127.0.0.1', '2025-03-16 18:16:45.33315');
INSERT INTO public.admin_operation_logs VALUES (2, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '更新分销等级', 'level', '3', '{"method": "PUT", "url": "/api/admin/v2/distribution-levels/3", "args": {}, "body": {"level": 3, "commission_rate": 5, "description": "\u4e09\u7ea7\u5206\u9500", "is_active": true}, "status_code": 200}', '127.0.0.1', '2025-03-16 18:17:31.881178');


--
-- Data for Name: admin_users; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

INSERT INTO public.admin_users VALUES (1, '0x123456789012345678901234567890123456abcd', '超级管理员', 'super_admin', '{管理用户,管理资产,管理佣金,审核资产,管理设置,管理管理员,查看日志,管理仪表盘}', NULL, '2025-03-16 03:38:52.807818', '2025-03-16 03:38:52.809264');
INSERT INTO public.admin_users VALUES (2, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', 'SOL管理员', 'super_admin', '{管理用户,管理资产,管理佣金,审核资产,管理设置,管理管理员,查看日志,管理仪表盘}', NULL, '2025-03-16 03:50:02.624455', '2025-03-16 03:50:02.62512');


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

INSERT INTO public.alembic_version VALUES ('ce5a4d540c25');


--
-- Data for Name: assets; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

INSERT INTO public.assets VALUES (4, 'BTC ETF', 'BTC ETF (Bitcoin Exchange-Traded Fund) is a financial instrument that allows investors to gain exposure to Bitcoin through traditional stock markets. By tracking the price of Bitcoin, it provides a convenient, secure, and compliant way for investors to participate in the cryptocurrency market without directly holding Bitcoin.', 20, 'COINBASE', NULL, 10000000, 'RH-205874', 0.1, 100000000, NULL, 1000000, '["/static/uploads/20/temp/image/1740499081_premier-etf-bitcoin.jpg"]', NULL, 1, NULL, '0x6394993426dba3b654ef0052698fe9e0b6a98870', '0x6394993426dba3b654ef0052698fe9e0b6a98870', '2025-02-25 15:58:03.462315', '2025-03-12 15:39:36.018243', NULL, 100000000, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, false, NULL);
INSERT INTO public.assets VALUES (10, 'Palm Jumeirah Luxury Villa 8101', '12332', 10, '8101 Palm Jumeirah Road, Dubai, UAE', 12311, 12312311, 'RH-101727', 0.100011, 123110000, 'So7gwf7Pc4Dtawbi7Ee7TeSiLjUMh6AyLqCH4ZxL3n', 1, '["/static/uploads/projects/RH-10338683/images/file_1742234193001_1.jpeg", "/static/uploads/projects/RH-10338683/images/file_1742234198204_1.jpeg", "/static/uploads/projects/RH-10338683/images/file_1742234198382_1.jpeg", "/static/uploads/projects/RH-10338683/images/file_1742234198421_1.jpeg"]', '[{"name": "DeepSeek\u4ece\u5165\u95e8\u5230\u7cbe\u901a(20250204).pdf", "url": "/static/uploads/projects/RH-205710/documents/file_1742235293349_1.pdf"}]', 2, NULL, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-18 13:49:50.843079', '2025-03-18 13:49:50.843083', NULL, 123110000, '{"network": "solana", "token_type": "spl", "decimals": 9, "deployment_time": "2025-03-18T21:49:50.841529"}', NULL, NULL, false, NULL, NULL, NULL, NULL, NULL, false, NULL);
INSERT INTO public.assets VALUES (2, 'Palm Jumeirah Luxury Villa 8101', 'This villa is located on Palm Jumeirah in Dubai, with a private pool and beach, luxurious interiors, making it an ideal choice for high-end living.', 10, '8101 Palm Jumeirah Road, Dubai, UAE', 4000, 23000000, 'RH-109774', 0.575, 40000000, NULL, 120000, '["/static/uploads/10/temp/image/1740481324_DSC_1851_103.jpg", "/static/uploads/10/temp/image/1740481328_Frond-M-Palm-Jumeirah-Dubai-Dubai-United-Arab-Emirates-20.jpg", "/static/uploads/10/temp/image/1740481328_Frond-M-Palm-Jumeirah-Dubai-Dubai-United-Arab-Emirates-1.jpg", "/static/uploads/10/temp/image/1740481328_Frond-M-Palm-Jumeirah-Dubai-Dubai-United-Arab-Emirates-21.jpg", "/static/uploads/10/temp/image/1740481328_DSC_3828_51-Copy-Copy-2.jpg", "/static/uploads/10/temp/image/1740481332_1100xxs.webp", "/static/uploads/10/temp/image/1740481332_922248_38433.webp"]', NULL, 2, NULL, '0x6394993426dba3b654ef0052698fe9e0b6a98870', '0x6394993426dba3b654ef0052698fe9e0b6a98870', '2025-02-25 11:02:27.595321', '2025-03-16 20:18:04.541537', NULL, 39999867, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, false, NULL);
INSERT INTO public.assets VALUES (3, 'BTC ETF', 'BTC ETF (Bitcoin Exchange-Traded Fund) is a financial instrument that allows investors to gain exposure to Bitcoin through traditional stock markets. By tracking the price of Bitcoin, it provides a convenient, secure, and compliant way for investors to participate in the cryptocurrency market without directly holding Bitcoin.', 20, 'COINBASE', NULL, 100000000, 'RH-209003', 1, 100000000, NULL, 1000000, '["/static/uploads/20/temp/image/1740481479_premier-etf-bitcoin.jpg"]', NULL, 1, NULL, '0x6394993426dba3b654ef0052698fe9e0b6a98870', '0x6394993426dba3b654ef0052698fe9e0b6a98870', '2025-02-25 11:04:51.732714', '2025-03-12 15:39:36.018242', NULL, 100000000, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, false, NULL);
INSERT INTO public.assets VALUES (9, 'Palm Jumeirah Luxury Villa 8101', '12332', 10, '8101 Palm Jumeirah Road, Dubai, UAE', 12311, 12312311, 'RH-101719', 0.100011, 123110000, 'So7AoJw2CAEj3GL73eZo7YVbqhfDDvN5w3aerk5o4j', 1, '["/static/uploads/projects/RH-10338683/images/file_1742234193001_1.jpeg", "/static/uploads/projects/RH-10338683/images/file_1742234198204_1.jpeg", "/static/uploads/projects/RH-10338683/images/file_1742234198382_1.jpeg", "/static/uploads/projects/RH-10338683/images/file_1742234198421_1.jpeg"]', '[{"name": "DeepSeek\u4ece\u5165\u95e8\u5230\u7cbe\u901a(20250204).pdf", "url": "/static/uploads/projects/RH-205710/documents/file_1742235293349_1.pdf"}]', 2, NULL, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-18 13:46:40.222996', '2025-03-18 13:46:40.223001', NULL, 123110000, '{"network": "solana", "token_type": "spl", "decimals": 9, "deployment_time": "2025-03-18T21:46:40.218740"}', NULL, NULL, false, NULL, NULL, NULL, NULL, NULL, false, NULL);
INSERT INTO public.assets VALUES (11, 'Palm Jumeirah Luxury Villa 8101', '12332', 10, '8101 Palm Jumeirah Road, Dubai, UAE', 12311, 123123111, 'RH-101409', 1.000106, 123110000, 'SoEDfdgwDYLGr5TkrXdQ3bRAwi11jo7FCdeJboeAMi', 1, '["/static/uploads/projects/RH-101409/images/1742319935_photo-1583953458882-302655b5c376.jpeg", "/static/uploads/projects/RH-101409/images/1742319935_photo-1583830379747-195159d0de82.jpeg", "/static/uploads/projects/RH-101409/images/1742319935_photo-1581982231900-6a1a46b744c9.jpeg", "/static/uploads/projects/RH-101409/images/1742319935_Frond-M-Palm-Jumeirah-Dubai-Dubai-United-Arab-Emirates-20.jpg", "/static/uploads/projects/RH-101409/images/1742319935_DSC_1851_103.jpg", "/static/uploads/projects/RH-101409/images/1742319935_DSC_3828_51-Copy-Copy-2.jpg", "/static/uploads/projects/RH-101409/images/1742319935_palm-2-9-beachfront-hauteretreats.jpg", "/static/uploads/projects/RH-101409/images/1742319935_Frond-M-Palm-Jumeirah-Dubai-Dubai-United-Arab-Emirates-1.jpg", "/static/uploads/projects/RH-101409/images/1742319935_Frond-M-Palm-Jumeirah-Dubai-Dubai-United-Arab-Emirates-21.jpg"]', NULL, 2, NULL, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-18 17:45:50.481989', '2025-03-18 17:45:50.481991', NULL, 123110000, '{"network": "solana", "token_type": "spl", "decimals": 9, "deployment_time": "2025-03-19T01:45:50.477362"}', NULL, NULL, false, NULL, NULL, NULL, NULL, NULL, false, NULL);
INSERT INTO public.assets VALUES (12, 'Palm Jumeirah Luxury Villa 8101', '1221', 10, '8101 Palm Jumeirah Road, Dubai, UAE', 121, 1212, 'RH-106451', 0.001002, 1210000, 'SoENL8Pp914uyP4uFquKTTsYEkKyVdwdSE82H9zPN4', 1, '["/static/uploads/projects/RH-106451/images/1742461010_DSC_3828_51-Copy-Copy-2.jpg", "/static/uploads/projects/RH-106451/images/1742461010_palm-2-9-beachfront-hauteretreats.jpg", "/static/uploads/projects/RH-106451/images/1742461010_Frond-M-Palm-Jumeirah-Dubai-Dubai-United-Arab-Emirates-1.jpg", "/static/uploads/projects/RH-106451/images/1742461010_Frond-M-Palm-Jumeirah-Dubai-Dubai-United-Arab-Emirates-21.jpg"]', NULL, 2, NULL, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-20 09:36:23.665072', '2025-03-20 09:36:23.665076', NULL, 1210000, '{"network": "solana", "token_type": "spl", "decimals": 9, "deployment_time": "2025-03-20T17:36:23.660910"}', NULL, NULL, false, NULL, NULL, NULL, NULL, NULL, false, NULL);
INSERT INTO public.assets VALUES (13, 'Palm Jumeirah Luxury Villa 8101', '1221', 10, '8101 Palm Jumeirah Road, Dubai, UAE', 121, 1212, 'RH-106046', 0.001002, 1210000, 'SoDiVXmWXx65ueRKTEUjzcWMMGg43RCjhG5cA6vfTV', 1, '["/static/uploads/projects/RH-106451/images/1742461010_DSC_3828_51-Copy-Copy-2.jpg", "/static/uploads/projects/RH-106451/images/1742461010_palm-2-9-beachfront-hauteretreats.jpg", "/static/uploads/projects/RH-106451/images/1742461010_Frond-M-Palm-Jumeirah-Dubai-Dubai-United-Arab-Emirates-1.jpg", "/static/uploads/projects/RH-106451/images/1742461010_Frond-M-Palm-Jumeirah-Dubai-Dubai-United-Arab-Emirates-21.jpg"]', NULL, 2, NULL, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-20 09:37:03.21499', '2025-03-20 09:37:03.214994', NULL, 1210000, '{"network": "solana", "token_type": "spl", "decimals": 9, "deployment_time": "2025-03-20T17:37:03.213900"}', NULL, NULL, false, NULL, NULL, NULL, NULL, NULL, false, NULL);
INSERT INTO public.assets VALUES (14, 'Palm Jumeirah Luxury Villa 8101', '1221', 10, '8101 Palm Jumeirah Road, Dubai, UAE', 121, 111, 'RH-102535', 9.2e-05, 1210000, 'So6Uxagq4JuofKZvK2GQqifAkbz5Km6qbeXJhHmRCo', 1, '["/static/uploads/projects/RH-106451/images/1742461010_DSC_3828_51-Copy-Copy-2.jpg", "/static/uploads/projects/RH-106451/images/1742461010_palm-2-9-beachfront-hauteretreats.jpg", "/static/uploads/projects/RH-106451/images/1742461010_Frond-M-Palm-Jumeirah-Dubai-Dubai-United-Arab-Emirates-1.jpg", "/static/uploads/projects/RH-106451/images/1742461010_Frond-M-Palm-Jumeirah-Dubai-Dubai-United-Arab-Emirates-21.jpg"]', NULL, 2, NULL, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-21 08:56:53.946317', '2025-03-21 08:56:53.946321', NULL, 1210000, '{"network": "solana", "token_type": "spl", "decimals": 9, "deployment_time": "2025-03-21T16:56:53.942959"}', NULL, '{"tx_hash": "0xeff1b4d8e6538eb754174c73c6769434f48189b0b130fd2af1030992c4280804", "platform_address": "HnPZkg9FpHjovNNZ8Au1MyLjYPbW9KsK87ACPCh1SvSd"}', true, '2025-03-21 08:56:53.942988', NULL, NULL, NULL, NULL, false, NULL);
INSERT INTO public.assets VALUES (16, '自动化测试资产', '用于验证自动上链系统的测试资产', 20, '测试地址', NULL, 1000, 'RH-209999', 1, 1000, NULL, 100, NULL, NULL, 1, NULL, '11111111111111111111111111111111', '11111111111111111111111111111111', '2025-05-27 11:43:49.310431', '2025-05-27 03:43:49.311541', NULL, 1000, NULL, NULL, NULL, false, NULL, NULL, NULL, 'test_tx_hash_1748317429', NULL, false, NULL);
INSERT INTO public.assets VALUES (20, 'Siberian Green Energy BTC Mining Center', '绿色能源比特币挖矿中心测试资产', 10, 'Siberia, Russia', 5000, 100000, 'RH-209342', 100, 50000000, NULL, 10000, NULL, NULL, 2, NULL, '6UrwhN2rqQvo2tBfc9FZCdUbt9JLs3BJiEm7pv4NM41b', '6UrwhN2rqQvo2tBfc9FZCdUbt9JLs3BJiEm7pv4NM41b', '2025-05-27 13:36:03.806223', '2025-07-23 04:16:02.277581', NULL, 50000000, NULL, NULL, NULL, false, NULL, NULL, NULL, NULL, NULL, false, NULL);


--
-- Data for Name: asset_status_history; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--



--
-- Data for Name: commission_config; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

INSERT INTO public.commission_config VALUES (1, 'commission_rate', '35.0', '推荐佣金比例', true, '2025-05-26 15:51:19.283657', '2025-05-26 15:52:41.620056');
INSERT INTO public.commission_config VALUES (4, 'test_rate', '25.0', '测试佣金比例', true, '2025-05-26 15:58:03.675046', '2025-05-26 16:14:14.551115');
INSERT INTO public.commission_config VALUES (2, 'min_withdraw_amount', '10.0', '最低提现金额', true, '2025-05-26 15:51:19.287361', '2025-05-26 16:14:14.739578');
INSERT INTO public.commission_config VALUES (3, 'withdraw_delay_minutes', '1', '提现延迟分钟数', true, '2025-05-26 15:51:19.288302', '2025-05-26 16:14:14.740922');


--
-- Data for Name: trades; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

INSERT INTO public.trades VALUES (81, 2, 'buy', 2, 0.575, 'eeyfrdpgtdtm9pldrxfq39c2skyd9sqkijw7keukjtlr', '2025-03-13 13:42:54.571454', false, 'mock_1741873377587_meg1z3q4pah', 'completed', NULL, 1.15, 0.00575, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (83, 2, 'buy', 1, 0.575, 'eeyfrdpgtdtm9pldrxfq39c2skyd9sqkijw7keukjtlr', '2025-03-13 14:22:11.378808', false, 'mock_1741875734395_274gopvsc9b', 'completed', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (85, 2, 'buy', 2, 0.575, 'eeyfrdpgtdtm9pldrxfq39c2skyd9sqkijw7keukjtlr', '2025-03-13 14:51:37.111535', false, 'mock_1741877500120_xg4mpvol79f', 'completed', NULL, 1.15, 0.00575, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (88, 2, 'buy', 10, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-13 16:03:45.554951', false, 'mock_1741881828613_yi9wr3s5dj8', 'completed', NULL, 5.75, 0.02875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (91, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-16 18:57:06.311674', false, 'mock_1742151429340_8xc2al7pwzc', 'completed', NULL, 0.575, 0.020125, 0.035, NULL, NULL);
INSERT INTO public.trades VALUES (92, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-16 19:10:41.293602', false, 'mock_1742152244304_7n6uib122xa', 'completed', NULL, 0.575, 0.020125, 0.035, NULL, NULL);
INSERT INTO public.trades VALUES (96, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-16 20:00:37.814415', false, 'mock_1742155240823_seyzt0arscb', 'completed', NULL, 0.575, 0.020125, 0.035, NULL, NULL);
INSERT INTO public.trades VALUES (99, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-16 20:03:56.997103', false, 'mock_1742155440012_6o9dxppcgf2', 'completed', NULL, 0.575, 0.020125, 0.035, NULL, NULL);
INSERT INTO public.trades VALUES (102, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-16 20:06:47.678122', false, 'mock_1742155610693_mtz9exf1dq', 'completed', NULL, 0.575, 0.020125, 0.035, NULL, NULL);
INSERT INTO public.trades VALUES (105, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-17 06:01:06.692257', false, NULL, 'pending', NULL, 0.575, 0.020125, 0.035, NULL, NULL);
INSERT INTO public.trades VALUES (108, 10, 'buy', 3, 0.100011, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-18 16:07:08.185451', true, NULL, 'pending', NULL, 0.300033, 0.000300033, 0.001, NULL, NULL);
INSERT INTO public.trades VALUES (111, 2, 'buy', 100, 0.575, '0x6394993426dba3b654ef0052698fe9e0b6a98870', '2025-03-19 12:47:21.129065', true, NULL, 'pending', NULL, 57.49999999999999, 0.057499999999999996, 0.001, NULL, NULL);
INSERT INTO public.trades VALUES (2, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 01:34:01.912501', false, NULL, 'pending', NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.trades VALUES (3, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 01:36:39.563303', false, NULL, 'pending', NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.trades VALUES (82, 2, 'buy', 1, 0.575, 'eeyfrdpgtdtm9pldrxfq39c2skyd9sqkijw7keukjtlr', '2025-03-13 13:43:12.085989', false, 'mock_1741873395101_gpn7i9gmvb7', 'completed', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (86, 2, 'buy', 1, 0.575, 'eeyfrdpgtdtm9pldrxfq39c2skyd9sqkijw7keukjtlr', '2025-03-13 15:17:51.986367', false, 'mock_1741879074996_llicbmr5wd', 'completed', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (89, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-16 16:03:33.387021', false, 'mock_1742141016404_s5ddqxtbcdb', 'completed', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (94, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-16 19:57:29.73411', false, NULL, 'pending', NULL, 0.575, 0.020125, 0.035, NULL, NULL);
INSERT INTO public.trades VALUES (97, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-16 20:01:53.023494', false, 'mock_1742155316032_wectcakdo7f', 'completed', NULL, 0.575, 0.020125, 0.035, NULL, NULL);
INSERT INTO public.trades VALUES (100, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-16 20:05:36.946576', false, 'mock_1742155539964_b2hnh0fhjmd', 'completed', NULL, 0.575, 0.020125, 0.035, NULL, NULL);
INSERT INTO public.trades VALUES (103, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-16 20:08:30.609813', false, 'mock_1742155713627_cvn2vw5ye3v', 'completed', NULL, 0.575, 0.020125, 0.035, NULL, NULL);
INSERT INTO public.trades VALUES (106, 2, 'buy', 2, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-17 06:06:33.21776', false, NULL, 'pending', NULL, 1.15, 0.04025, 0.035, NULL, NULL);
INSERT INTO public.trades VALUES (109, 2, 'buy', 11, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-18 18:58:40.766895', false, NULL, 'pending', NULL, 6.324999999999999, 0.221375, 0.035, NULL, NULL);
INSERT INTO public.trades VALUES (112, 13, 'buy', 100, 0.001002, 'HnPZkg9FpHjovNNZ8Au1MyLjYPbW9KsK87ACPCh1SvSd', '2025-03-21 03:37:17.584328', false, NULL, 'pending', NULL, 0.10020000000000001, 0.0035070000000000006, 0.035, NULL, NULL);
INSERT INTO public.trades VALUES (113, 14, 'buy', 100, 9.2e-05, '8cU6PAtRTRgfyJu48qfz2hQP5aMGwooxqrCZtyB6UcYP', '2025-03-21 14:10:19.289388', false, NULL, 'pending', NULL, 0.0092, 0.000322, 0.035, NULL, NULL);
INSERT INTO public.trades VALUES (8, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 07:57:26.79552', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (9, 2, 'buy', 2, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 07:57:40.356791', false, NULL, 'pending', NULL, 1.15, 0.00575, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (10, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 08:02:57.968949', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (11, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 08:35:31.387406', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (4, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 01:47:02.806353', false, 'mock_1741657622_Ev6fjJQR1p5rgWKQ8pH6Yu2tVSwLzQPp', 'completed', 452470.0, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.trades VALUES (5, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 01:48:03.318717', false, 'mock_1741657683_gv92RGSj2UWdDkLQzFFE3Qo9qmaZetKA', 'completed', 223715.0, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.trades VALUES (6, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 02:09:43.12098', false, 'mock_1741658983_ZADEqioxxGmLCTeP1r5mbf5KXzNiFH1z', 'completed', 324145.0, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.trades VALUES (7, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 07:10:42.263731', false, 'mock_1741677042_wt6zh7Cz2w1QvZxeDAD8pqmFcBpu6zGZ', 'completed', 392463, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (12, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 08:35:43.357544', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (13, 2, 'buy', 4, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 08:36:01.968023', false, NULL, 'pending', NULL, 2.3, 0.0115, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (14, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 08:50:56.950477', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (15, 2, 'buy', 100, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 08:51:07.604542', false, NULL, 'pending', NULL, 57.49999999999999, 0.2875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (16, 2, 'buy', 2322, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 08:53:30.971523', false, NULL, 'pending', NULL, 1335.1499999999999, 6.67575, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (17, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 09:21:08.318927', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (18, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 09:31:43.58982', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (19, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 10:26:46.290785', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (20, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 14:06:07.411956', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (21, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 15:00:01.475815', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (22, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 15:08:54.360278', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (23, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 15:09:45.746155', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (24, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 15:10:00.126374', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (25, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 15:54:51.347659', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (26, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 16:05:13.447889', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (27, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 16:07:18.830289', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (28, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 16:21:54.655306', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (29, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 16:22:02.972352', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (30, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 16:22:17.006642', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (31, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 16:29:21.065746', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (32, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 16:29:29.763004', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (33, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 16:34:15.795374', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (34, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 16:34:24.14688', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (35, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 16:34:38.989301', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (36, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-11 16:35:47.748019', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (37, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-12 05:07:06.337584', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (38, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-12 05:07:25.012396', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (39, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-12 05:22:18.71087', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (40, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-12 05:22:27.444989', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (41, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-12 05:27:52.184741', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (42, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-12 05:28:01.760034', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (43, 2, 'buy', 190, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-12 05:28:11.006242', false, NULL, 'pending', NULL, 109.24999999999999, 0.5462499999999999, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (44, 2, 'buy', 134, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-12 05:28:49.908681', false, NULL, 'pending', NULL, 77.05, 0.38525, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (45, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-12 09:10:54.742154', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (46, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-12 09:11:02.053127', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (47, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-12 09:11:11.215304', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (48, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-12 09:21:22.613331', false, 'mock_1741771285626_j6zg9afa5so', 'completed', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (49, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-12 09:21:30.362901', false, 'mock_1741771293372_y0pqzwz5p6', 'completed', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (50, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-12 09:21:44.404794', false, 'mock_1741771307416_i3ihxih8cgi', 'completed', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (51, 2, 'buy', 2, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-12 09:22:20.829135', false, 'mock_1741771343838_ujh9verq9qr', 'completed', NULL, 1.15, 0.00575, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (52, 2, 'buy', 3, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-12 15:06:22.874899', false, 'mock_1741791985889_ixcrhz176gk', 'completed', NULL, 1.7249999999999999, 0.008624999999999999, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (53, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-12 16:11:48.72489', false, NULL, 'pending', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (54, 2, 'buy', 2, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-12 16:12:10.851048', false, NULL, 'pending', NULL, 1.15, 0.00575, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (55, 2, 'buy', 5, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-12 16:20:48.179399', false, 'mock_1741796451191_ly3o5sxubdi', 'completed', NULL, 2.875, 0.014375, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (56, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-12 16:33:31.067868', false, 'mock_1741797214081_krj6qbda6y8', 'completed', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (57, 2, 'buy', 2, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-12 16:33:48.22228', false, 'mock_1741797231236_22ac66bsewv', 'completed', NULL, 1.15, 0.00575, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (58, 2, 'buy', 3, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-12 16:33:56.759014', false, 'mock_1741797239765_h8hggr1kw1n', 'completed', NULL, 1.7249999999999999, 0.008624999999999999, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (59, 2, 'buy', 4, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-12 16:34:02.741964', false, 'mock_1741797245762_uuhizajmno', 'completed', NULL, 2.3, 0.0115, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (60, 2, 'buy', 5, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-12 16:34:10.199932', false, NULL, 'completed', NULL, 2.875, 0.014375, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (61, 2, 'buy', 6, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-12 16:37:17.549442', false, 'mock_1741797440587_z3rcix96n4h', 'completed', NULL, 3.4499999999999997, 0.017249999999999998, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (62, 2, 'buy', 7, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-12 16:37:33.069605', false, 'mock_1741797456086_8ak9j7aevl5', 'completed', NULL, 4.0249999999999995, 0.020124999999999997, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (63, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-12 23:57:17.945374', false, 'mock_1741823840964_wbylppgor3s', 'completed', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (64, 2, 'buy', 4, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-12 23:57:52.778012', false, 'mock_1741823875795_zrix662ayc', 'completed', NULL, 2.3, 0.0115, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (65, 2, 'buy', 5, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-13 00:51:06.290646', false, 'mock_1741827069304_jpp8c8actg', 'completed', NULL, 2.875, 0.014375, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (66, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-13 06:04:00.109373', false, 'mock_1741845843127_6avprjp4iqh', 'completed', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (67, 2, 'buy', 2, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-13 06:04:08.681488', false, 'mock_1741845851695_gw43q1lld7q', 'completed', NULL, 1.15, 0.00575, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (68, 2, 'buy', 3, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-13 06:17:36.106661', false, 'mock_1741846659117_4pr3pj0wybb', 'completed', NULL, 1.7249999999999999, 0.008624999999999999, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (69, 2, 'buy', 2, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-13 07:36:26.768457', false, NULL, 'pending', NULL, 1.15, 0.00575, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (70, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-13 08:04:16.689091', false, 'mock_1741853059702_9pxsrpjvnn9', 'completed', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (71, 2, 'buy', 4, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-13 08:15:43.69141', false, 'mock_1741853746720_kmiqg76lrdr', 'completed', NULL, 2.3, 0.0115, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (72, 2, 'buy', 3, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-13 08:16:01.990233', false, 'mock_1741853765007_ip0fdjm297h', 'completed', NULL, 1.7249999999999999, 0.008624999999999999, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (73, 2, 'buy', 6, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-13 08:18:13.601985', false, 'mock_1741853896612_p4bwgb0113', 'completed', NULL, 3.4499999999999997, 0.017249999999999998, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (74, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-13 12:39:50.693203', false, 'mock_1741869593705_r3htny9df1s', 'completed', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (75, 2, 'buy', 2, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-13 12:40:48.870357', false, 'mock_1741869651878_93davb2nvhv', 'completed', NULL, 1.15, 0.00575, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (76, 2, 'buy', 3, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-13 12:50:41.462234', false, 'mock_1741870244475_sfw3yn6lkqf', 'completed', NULL, 1.7249999999999999, 0.008624999999999999, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (77, 2, 'buy', 4, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-13 12:51:15.858631', false, 'mock_1741870278871_omost1uw7j', 'completed', NULL, 2.3, 0.0115, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (78, 2, 'buy', 5, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-13 12:58:08.059793', false, 'mock_1741870691071_ftztmhjkbk8', 'completed', NULL, 2.875, 0.014375, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (79, 2, 'buy', 4, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-13 13:04:06.40009', false, 'mock_1741871049414_iezmrcajkcc', 'completed', NULL, 2.3, 0.0115, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (80, 2, 'buy', 3, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-13 13:14:12.391221', false, 'mock_1741871655409_n2lmjxeva7k', 'completed', NULL, 1.7249999999999999, 0.008624999999999999, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (84, 2, 'buy', 1, 0.575, 'eeyfrdpgtdtm9pldrxfq39c2skyd9sqkijw7keukjtlr', '2025-03-13 14:51:21.02022', false, 'mock_1741877484032_87uyuywc6wx', 'completed', NULL, 0.575, 0.002875, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (87, 2, 'buy', 2, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-13 15:47:39.363903', false, 'mock_1741880862381_ijvy8k2tdcp', 'completed', NULL, 1.15, 0.00575, 0.005, NULL, NULL);
INSERT INTO public.trades VALUES (90, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-16 18:55:37.451394', false, NULL, 'failed', NULL, 0.575, 0.020125, 0.035, NULL, NULL);
INSERT INTO public.trades VALUES (93, 2, 'buy', 2, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-16 19:11:11.069502', false, 'mock_1742152274090_m2qk7gd81v', 'completed', NULL, 1.15, 0.04025, 0.035, NULL, NULL);
INSERT INTO public.trades VALUES (95, 2, 'buy', 3, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-16 19:58:50.397324', false, NULL, 'pending', NULL, 1.7249999999999999, 0.060375, 0.035, NULL, NULL);
INSERT INTO public.trades VALUES (98, 2, 'buy', 1, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-16 20:03:03.029528', false, 'mock_1742155386041_4pq7v16fz3', 'completed', NULL, 0.575, 0.020125, 0.035, NULL, NULL);
INSERT INTO public.trades VALUES (101, 2, 'buy', 2, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-16 20:06:02.04203', false, 'mock_1742155565062_9rseqmmgrj5', 'completed', NULL, 1.15, 0.04025, 0.035, NULL, NULL);
INSERT INTO public.trades VALUES (104, 2, 'buy', 2, 0.575, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-16 20:18:01.499463', false, 'mock_1742156284521_3p8lsoz7red', 'completed', NULL, 1.15, 0.04025, 0.035, NULL, NULL);
INSERT INTO public.trades VALUES (107, 10, 'buy', 100, 0.100011, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-18 16:04:36.785898', true, NULL, 'pending', NULL, 10.001100000000001, 0.0100011, 0.001, NULL, NULL);
INSERT INTO public.trades VALUES (110, 11, 'buy', 100, 1.000106, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-19 00:32:03.570541', true, NULL, 'pending', NULL, 100.0106, 0.1000106, 0.001, NULL, NULL);
INSERT INTO public.trades VALUES (114, 14, 'buy', 140, 9.2e-05, '8cU6PAtRTRgfyJu48qfz2hQP5aMGwooxqrCZtyB6UcYP', '2025-03-21 14:12:21.033078', false, NULL, 'pending', NULL, 0.01288, 0.00045080000000000006, 0.035, NULL, NULL);


--
-- Data for Name: commission_records; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

INSERT INTO public.commission_records VALUES (1, 96, 2, '0x0000000000000000000000000000000000000000', 0.020125, 'USDC', 'platform', 'paid', '2025-03-16 20:00:37.830593', '2025-03-16 20:00:40.892893', NULL);
INSERT INTO public.commission_records VALUES (2, 97, 2, '0x0000000000000000000000000000000000000000', 0.020125, 'USDC', 'platform', 'paid', '2025-03-16 20:01:53.040746', '2025-03-16 20:01:56.056418', NULL);
INSERT INTO public.commission_records VALUES (3, 98, 2, '0x0000000000000000000000000000000000000000', 0.020125, 'USDC', 'platform', 'pending', '2025-03-16 20:03:03.035035', '2025-03-16 20:03:03.035039', NULL);
INSERT INTO public.commission_records VALUES (4, 98, 2, '0x0000000000000000000000000000000000000000', 0.020125, 'USDC', 'platform', 'pending', '2025-03-16 20:03:06.06698', '2025-03-16 20:03:06.066981', NULL);
INSERT INTO public.commission_records VALUES (5, 99, 2, '0x0000000000000000000000000000000000000000', 0.020125, 'USDC', 'platform', 'pending', '2025-03-16 20:03:57.007667', '2025-03-16 20:03:57.00767', NULL);
INSERT INTO public.commission_records VALUES (6, 99, 2, '0x0000000000000000000000000000000000000000', 0.020125, 'USDC', 'platform', 'pending', '2025-03-16 20:04:00.028448', '2025-03-16 20:04:00.028451', NULL);
INSERT INTO public.commission_records VALUES (7, 100, 2, '0x0000000000000000000000000000000000000000', 0.020125, 'USDC', 'platform', 'pending', '2025-03-16 20:05:36.956965', '2025-03-16 20:05:36.95697', NULL);
INSERT INTO public.commission_records VALUES (8, 100, 2, '0x0000000000000000000000000000000000000000', 0.020125, 'USDC', 'platform', 'pending', '2025-03-16 20:05:39.980039', '2025-03-16 20:05:39.98004', NULL);
INSERT INTO public.commission_records VALUES (9, 101, 2, '0x0000000000000000000000000000000000000000', 0.04025, 'USDC', 'platform', 'pending', '2025-03-16 20:06:02.05244', '2025-03-16 20:06:02.052444', NULL);
INSERT INTO public.commission_records VALUES (10, 101, 2, '0x0000000000000000000000000000000000000000', 0.04025, 'USDC', 'platform', 'pending', '2025-03-16 20:06:05.081278', '2025-03-16 20:06:05.081279', NULL);
INSERT INTO public.commission_records VALUES (11, 102, 2, '0x0000000000000000000000000000000000000000', 0.020125, 'USDC', 'platform', 'pending', '2025-03-16 20:06:47.68625', '2025-03-16 20:06:47.686254', NULL);
INSERT INTO public.commission_records VALUES (12, 102, 2, '0x0000000000000000000000000000000000000000', 0.020125, 'USDC', 'platform', 'pending', '2025-03-16 20:06:50.721114', '2025-03-16 20:06:50.721117', NULL);
INSERT INTO public.commission_records VALUES (13, 103, 2, '0x0000000000000000000000000000000000000000', 0.020125, 'USDC', 'platform', 'pending', '2025-03-16 20:08:30.620089', '2025-03-16 20:08:30.620092', NULL);
INSERT INTO public.commission_records VALUES (14, 103, 2, '0x0000000000000000000000000000000000000000', 0.020125, 'USDC', 'platform', 'pending', '2025-03-16 20:08:33.659603', '2025-03-16 20:08:33.659604', NULL);
INSERT INTO public.commission_records VALUES (15, 104, 2, '0x0000000000000000000000000000000000000000', 0.04025, 'USDC', 'platform', 'pending', '2025-03-16 20:18:01.512802', '2025-03-16 20:18:01.512805', NULL);
INSERT INTO public.commission_records VALUES (16, 104, 2, '0x0000000000000000000000000000000000000000', 0.04025, 'USDC', 'platform', 'pending', '2025-03-16 20:18:04.5451', '2025-03-16 20:18:04.545105', NULL);
INSERT INTO public.commission_records VALUES (17, 107, 10, '0x0000000000000000000000000000000000000000', 0.0100011, 'USDC', 'platform', 'pending', '2025-03-18 16:04:36.798615', '2025-03-18 16:04:36.798617', NULL);
INSERT INTO public.commission_records VALUES (18, 108, 10, '0x0000000000000000000000000000000000000000', 0.000300033, 'USDC', 'platform', 'pending', '2025-03-18 16:07:08.196015', '2025-03-18 16:07:08.196024', NULL);
INSERT INTO public.commission_records VALUES (19, 109, 2, '0x0000000000000000000000000000000000000000', 0.221375, 'USDC', 'platform', 'pending', '2025-03-18 18:58:40.799338', '2025-03-18 18:58:40.799342', NULL);
INSERT INTO public.commission_records VALUES (20, 110, 11, '0x0000000000000000000000000000000000000000', 0.1000106, 'USDC', 'platform', 'pending', '2025-03-19 00:32:03.583357', '2025-03-19 00:32:03.58336', NULL);
INSERT INTO public.commission_records VALUES (21, 111, 2, '0x0000000000000000000000000000000000000000', 0.057499999999999996, 'USDC', 'platform', 'pending', '2025-03-19 12:47:21.152128', '2025-03-19 12:47:21.152132', NULL);
INSERT INTO public.commission_records VALUES (22, 112, 13, '0x0000000000000000000000000000000000000000', 0.0035070000000000006, 'USDC', 'platform', 'pending', '2025-03-21 03:37:17.605012', '2025-03-21 03:37:17.605018', NULL);
INSERT INTO public.commission_records VALUES (23, 113, 14, '0x0000000000000000000000000000000000000000', 0.000322, 'USDC', 'platform', 'pending', '2025-03-21 14:10:19.312951', '2025-03-21 14:10:19.312952', NULL);
INSERT INTO public.commission_records VALUES (24, 114, 14, '0x0000000000000000000000000000000000000000', 0.00045080000000000006, 'USDC', 'platform', 'pending', '2025-03-21 14:12:21.058048', '2025-03-21 14:12:21.058051', NULL);


--
-- Data for Name: commission_settings; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

INSERT INTO public.commission_settings VALUES (1, NULL, 0.01, 100, 1000000, true, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-16 15:52:02.655307', '2025-03-16 15:52:02.655311');
INSERT INTO public.commission_settings VALUES (2, 10, 0.01, 100, 2000000, true, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-16 15:52:02.655312', '2025-03-16 15:52:02.655312');
INSERT INTO public.commission_settings VALUES (3, 20, 0.01, 100, 3000000, true, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-16 15:52:02.655312', '2025-03-16 15:52:02.655314');


--
-- Data for Name: commission_withdrawals; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

INSERT INTO public.commission_withdrawals VALUES (2, '0x1234567890123456789012345678901234567890', '0x9876543210987654321098765432109876543210', 25.75000000, 'USDC', 'completed', 1, '2025-05-26 15:58:03.762016', '2025-05-26 15:59:03.762016', '2025-05-26 15:58:03.767806', '0xabcdef123456', 0.05000000, 25.70000000, NULL, NULL, NULL, '2025-05-26 15:58:03.762659', '2025-05-26 15:58:03.767813');
INSERT INTO public.commission_withdrawals VALUES (3, '0x1234567890123456789012345678901234567890', '0x9876543210987654321098765432109876543210', 25.75000000, 'USDC', 'completed', 1, '2025-05-26 16:10:52.203642', '2025-05-26 16:11:52.203642', '2025-05-26 16:10:52.208326', '0xabcdef123456', 0.05000000, 25.70000000, NULL, NULL, NULL, '2025-05-26 16:10:52.204212', '2025-05-26 16:10:52.208333');
INSERT INTO public.commission_withdrawals VALUES (4, '0xtest123456789012345678901234567890', '0xwithdraw123456789012345678901234567890', 30.00000000, 'USDC', 'pending', 1, '2025-05-26 16:10:52.309884', '2025-05-26 16:11:52.309884', NULL, NULL, 0.00000000, NULL, NULL, NULL, NULL, '2025-05-26 16:10:52.310411', '2025-05-26 16:10:52.310411');
INSERT INTO public.commission_withdrawals VALUES (5, '0x1234567890123456789012345678901234567890', '0x9876543210987654321098765432109876543210', 25.75000000, 'USDC', 'completed', 1, '2025-05-26 16:12:19.467319', '2025-05-26 16:13:19.467319', '2025-05-26 16:12:19.471864', '0xabcdef123456', 0.05000000, 25.70000000, NULL, NULL, NULL, '2025-05-26 16:12:19.468031', '2025-05-26 16:12:19.471871');
INSERT INTO public.commission_withdrawals VALUES (6, '0xtest123456789012345678901234567890', '0xwithdraw123456789012345678901234567890', 30.00000000, 'USDC', 'completed', 1, '2025-05-26 16:12:19.568979', '2025-05-26 16:13:19.568979', '2025-05-26 16:12:19.572673', '0xtxhash123456', 0.05000000, 29.95000000, NULL, NULL, NULL, '2025-05-26 16:12:19.569347', '2025-05-26 16:12:19.572678');
INSERT INTO public.commission_withdrawals VALUES (7, '0x1234567890123456789012345678901234567890', '0x9876543210987654321098765432109876543210', 25.75000000, 'USDC', 'completed', 1, '2025-05-26 16:14:14.642972', '2025-05-26 16:15:14.642972', '2025-05-26 16:14:14.646758', '0xabcdef123456', 0.05000000, 25.70000000, NULL, NULL, NULL, '2025-05-26 16:14:14.643646', '2025-05-26 16:14:14.646767');
INSERT INTO public.commission_withdrawals VALUES (8, '0xtest123456789012345678901234567890', '0xwithdraw123456789012345678901234567890', 30.00000000, 'USDC', 'completed', 1, '2025-05-26 16:14:14.743154', '2025-05-26 16:15:14.743154', '2025-05-26 16:14:14.747257', '0xtxhash123456', 0.05000000, 29.95000000, NULL, NULL, NULL, '2025-05-26 16:14:14.743505', '2025-05-26 16:14:14.747262');


--
-- Data for Name: commissions; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--



--
-- Data for Name: dashboard_stats; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

INSERT INTO public.dashboard_stats VALUES (8, '2025-03-16 00:00:00', 'user_count', 0, 'daily', '2025-03-16 18:34:58.077985', '2025-03-16 20:18:04.548289');
INSERT INTO public.dashboard_stats VALUES (13, '2025-03-16 00:00:00', 'new_users', 0, 'daily', '2025-03-16 18:34:58.10194', '2025-03-16 20:18:04.551652');
INSERT INTO public.dashboard_stats VALUES (9, '2025-03-16 00:00:00', 'asset_count', 3, 'daily', '2025-03-16 18:34:58.09019', '2025-03-16 20:18:04.562156');
INSERT INTO public.dashboard_stats VALUES (10, '2025-03-16 00:00:00', 'asset_value', 133000000, 'daily', '2025-03-16 18:34:58.09259', '2025-03-16 20:18:04.57139');
INSERT INTO public.dashboard_stats VALUES (11, '2025-03-16 00:00:00', 'trade_count', 16, 'daily', '2025-03-16 18:34:58.099316', '2025-03-16 20:18:04.576327');
INSERT INTO public.dashboard_stats VALUES (12, '2025-03-16 00:00:00', 'trade_volume', 12.075000000000001, 'daily', '2025-03-16 18:34:58.10129', '2025-03-16 20:18:04.578496');
INSERT INTO public.dashboard_stats VALUES (32, '2025-03-21 00:00:00', 'user_count', 0, 'daily', '2025-03-21 03:37:17.602813', '2025-03-21 14:12:21.039107');
INSERT INTO public.dashboard_stats VALUES (33, '2025-03-21 00:00:00', 'new_users', 0, 'daily', '2025-03-21 03:37:17.610542', '2025-03-21 14:12:21.041975');
INSERT INTO public.dashboard_stats VALUES (34, '2025-03-21 00:00:00', 'asset_count', 9, 'daily', '2025-03-21 03:37:17.61548', '2025-03-21 14:12:21.044418');
INSERT INTO public.dashboard_stats VALUES (35, '2025-03-21 00:00:00', 'asset_value', 280750268, 'daily', '2025-03-21 03:37:17.618984', '2025-03-21 14:12:21.046353');
INSERT INTO public.dashboard_stats VALUES (36, '2025-03-21 00:00:00', 'trade_count', 2, 'daily', '2025-03-21 03:37:17.623504', '2025-03-21 14:12:21.048223');
INSERT INTO public.dashboard_stats VALUES (37, '2025-03-21 00:00:00', 'trade_volume', 0.10940000000000001, 'daily', '2025-03-21 03:37:17.625231', '2025-03-21 14:12:21.04977');
INSERT INTO public.dashboard_stats VALUES (2, '2025-03-17 00:00:00', 'user_count', 0, 'daily', '2025-03-17 02:32:17.734643', '2025-03-17 19:35:48.82534');
INSERT INTO public.dashboard_stats VALUES (3, '2025-03-17 00:00:00', 'new_users', 0, 'daily', '2025-03-17 02:32:24.493575', '2025-03-17 19:35:48.8333');
INSERT INTO public.dashboard_stats VALUES (4, '2025-03-17 00:00:00', 'asset_count', 4, 'daily', '2025-03-17 02:32:24.493575', '2025-03-17 19:35:48.837697');
INSERT INTO public.dashboard_stats VALUES (5, '2025-03-17 00:00:00', 'asset_value', 134231233.89, 'daily', '2025-03-17 02:32:24.493575', '2025-03-17 19:35:48.839435');
INSERT INTO public.dashboard_stats VALUES (6, '2025-03-17 00:00:00', 'trade_count', 2, 'daily', '2025-03-17 02:32:24.493575', '2025-03-17 19:35:48.841813');
INSERT INTO public.dashboard_stats VALUES (7, '2025-03-17 00:00:00', 'trade_volume', 1.7249999999999999, 'daily', '2025-03-17 02:32:24.493575', '2025-03-17 19:35:48.843419');
INSERT INTO public.dashboard_stats VALUES (14, '2025-03-18 00:00:00', 'user_count', 0, 'daily', '2025-03-18 12:40:44.432239', '2025-03-18 18:58:40.781176');
INSERT INTO public.dashboard_stats VALUES (15, '2025-03-18 00:00:00', 'new_users', 0, 'daily', '2025-03-18 12:40:44.436836', '2025-03-18 18:58:40.799953');
INSERT INTO public.dashboard_stats VALUES (16, '2025-03-18 00:00:00', 'asset_count', 6, 'daily', '2025-03-18 12:40:44.439589', '2025-03-18 18:58:40.802839');
INSERT INTO public.dashboard_stats VALUES (17, '2025-03-18 00:00:00', 'asset_value', 280747733, 'daily', '2025-03-18 12:40:44.441381', '2025-03-18 18:58:40.804704');
INSERT INTO public.dashboard_stats VALUES (18, '2025-03-18 00:00:00', 'trade_count', 3, 'daily', '2025-03-18 12:40:44.44385', '2025-03-18 18:58:40.808349');
INSERT INTO public.dashboard_stats VALUES (19, '2025-03-18 00:00:00', 'trade_volume', 16.626133, 'daily', '2025-03-18 12:40:44.444978', '2025-03-18 18:58:40.810642');
INSERT INTO public.dashboard_stats VALUES (20, '2025-03-19 00:00:00', 'user_count', 0, 'daily', '2025-03-19 00:32:03.580958', '2025-03-19 12:47:21.143389');
INSERT INTO public.dashboard_stats VALUES (21, '2025-03-19 00:00:00', 'new_users', 0, 'daily', '2025-03-19 00:32:03.584454', '2025-03-19 12:47:21.152303');
INSERT INTO public.dashboard_stats VALUES (22, '2025-03-19 00:00:00', 'asset_count', 6, 'daily', '2025-03-19 00:32:03.586719', '2025-03-19 12:47:21.156536');
INSERT INTO public.dashboard_stats VALUES (23, '2025-03-19 00:00:00', 'asset_value', 280747733, 'daily', '2025-03-19 00:32:03.589216', '2025-03-19 12:47:21.159381');
INSERT INTO public.dashboard_stats VALUES (24, '2025-03-19 00:00:00', 'trade_count', 2, 'daily', '2025-03-19 00:32:03.591301', '2025-03-19 12:47:21.165432');
INSERT INTO public.dashboard_stats VALUES (25, '2025-03-19 00:00:00', 'trade_volume', 157.51059999999998, 'daily', '2025-03-19 00:32:03.593033', '2025-03-19 12:47:21.170058');
INSERT INTO public.dashboard_stats VALUES (26, '2025-03-20 00:00:00', 'user_count', 0, 'daily', '2025-03-20 09:36:23.691591', '2025-03-20 09:37:03.218559');
INSERT INTO public.dashboard_stats VALUES (27, '2025-03-20 00:00:00', 'new_users', 0, 'daily', '2025-03-20 09:36:23.697266', '2025-03-20 09:37:03.222297');
INSERT INTO public.dashboard_stats VALUES (28, '2025-03-20 00:00:00', 'asset_count', 8, 'daily', '2025-03-20 09:36:23.701811', '2025-03-20 09:37:03.226454');
INSERT INTO public.dashboard_stats VALUES (29, '2025-03-20 00:00:00', 'asset_value', 280750157, 'daily', '2025-03-20 09:36:23.703873', '2025-03-20 09:37:03.228903');
INSERT INTO public.dashboard_stats VALUES (30, '2025-03-20 00:00:00', 'trade_count', 0, 'daily', '2025-03-20 09:36:23.708201', '2025-03-20 09:37:03.230947');
INSERT INTO public.dashboard_stats VALUES (31, '2025-03-20 00:00:00', 'trade_volume', 0, 'daily', '2025-03-20 09:36:23.70981', '2025-03-20 09:37:03.232458');


--
-- Data for Name: distribution_levels; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

INSERT INTO public.distribution_levels VALUES (1, 1, 30, '一级分销', true, '2025-03-16 15:52:02.662182', '2025-03-16 15:52:02.662184');
INSERT INTO public.distribution_levels VALUES (2, 2, 15, '二级分销', true, '2025-03-16 15:52:02.662185', '2025-03-16 18:16:45.327171');
INSERT INTO public.distribution_levels VALUES (3, 3, 5, '三级分销', true, '2025-03-16 15:52:02.662185', '2025-03-16 18:17:31.878761');


--
-- Data for Name: distribution_settings; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

INSERT INTO public.distribution_settings VALUES (1, 1, 0.3, true, '2025-03-17 03:58:30.745188', '2025-03-17 03:58:30.745188');
INSERT INTO public.distribution_settings VALUES (2, 2, 0.15, true, '2025-03-17 03:58:30.745188', '2025-03-17 03:58:30.745188');
INSERT INTO public.distribution_settings VALUES (3, 3, 0.05, true, '2025-03-17 03:58:30.745188', '2025-03-17 03:58:30.745188');


--
-- Data for Name: dividend_records; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--



--
-- Data for Name: dividend_distributions; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--



--
-- Data for Name: dividends; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--



--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--



--
-- Data for Name: holdings; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--



--
-- Data for Name: ip_visits; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

INSERT INTO public.ip_visits VALUES (1, '127.0.0.1', 'Werkzeug/2.3.7', NULL, '/api/share-messages/random', '2025-05-31 05:08:40.176201', NULL, NULL);
INSERT INTO public.ip_visits VALUES (2, '127.0.0.1', 'Werkzeug/2.3.7', NULL, '/api/shortlink/create', '2025-05-31 05:08:40.184341', NULL, NULL);
INSERT INTO public.ip_visits VALUES (3, '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', NULL, '/', '2025-07-08 19:52:37.56404', NULL, NULL);
INSERT INTO public.ip_visits VALUES (4, '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', 'http://127.0.0.1:5001/', '/assets/', '2025-07-08 19:52:43.755857', NULL, NULL);
INSERT INTO public.ip_visits VALUES (5, '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', 'http://127.0.0.1:5001/assets/', '/assets/RH-102535', '2025-07-08 19:52:47.663334', NULL, NULL);
INSERT INTO public.ip_visits VALUES (6, '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', 'http://127.0.0.1:5001/assets/RH-102535', '/api/assets/symbol/RH-102535/dividend_stats', '2025-07-08 19:52:47.831801', NULL, NULL);
INSERT INTO public.ip_visits VALUES (7, '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', 'http://127.0.0.1:5001/assets/RH-102535', '/api/trades', '2025-07-08 19:52:47.833951', NULL, NULL);
INSERT INTO public.ip_visits VALUES (8, '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', NULL, '/v6', '2025-07-08 19:54:21.342048', NULL, NULL);
INSERT INTO public.ip_visits VALUES (9, '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', 'http://127.0.0.1:5001/v6', '/assets', '2025-07-08 19:55:47.970501', NULL, NULL);
INSERT INTO public.ip_visits VALUES (10, '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', 'http://127.0.0.1:5001/v6', '/assets/', '2025-07-08 19:55:47.985961', NULL, NULL);
INSERT INTO public.ip_visits VALUES (11, '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', 'http://127.0.0.1:5001/v6', '/portfolio', '2025-07-08 19:55:52.32123', NULL, NULL);
INSERT INTO public.ip_visits VALUES (12, '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', 'http://127.0.0.1:5001/v6', '/admin/login', '2025-07-08 19:56:35.528298', NULL, NULL);
INSERT INTO public.ip_visits VALUES (13, '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', 'http://127.0.0.1:5001/v6', '/admin/v2/login', '2025-07-08 19:56:35.540761', NULL, NULL);
INSERT INTO public.ip_visits VALUES (14, '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', 'http://127.0.0.1:5001/v6', '/admin/register', '2025-07-08 19:56:44.603913', NULL, NULL);
INSERT INTO public.ip_visits VALUES (15, '192.168.0.200', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', NULL, '/', '2025-07-08 20:08:44.225855', NULL, NULL);
INSERT INTO public.ip_visits VALUES (16, '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', NULL, '/', '2025-07-08 20:08:51.728559', NULL, NULL);
INSERT INTO public.ip_visits VALUES (17, '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', NULL, '/v6', '2025-07-08 20:09:01.314145', NULL, NULL);
INSERT INTO public.ip_visits VALUES (18, '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', NULL, '/v6', '2025-07-08 20:15:34.195317', NULL, NULL);
INSERT INTO public.ip_visits VALUES (19, '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', NULL, '/v6', '2025-07-08 20:15:36.284499', NULL, NULL);
INSERT INTO public.ip_visits VALUES (20, '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', NULL, '/', '2025-07-08 20:15:51.212081', NULL, NULL);
INSERT INTO public.ip_visits VALUES (21, '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', NULL, '/v6', '2025-07-08 20:16:19.007235', NULL, NULL);
INSERT INTO public.ip_visits VALUES (22, '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', NULL, '/v6', '2025-07-08 21:38:11.270899', NULL, NULL);
INSERT INTO public.ip_visits VALUES (23, '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', NULL, '/', '2025-07-08 21:38:24.069179', NULL, NULL);
INSERT INTO public.ip_visits VALUES (24, '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', NULL, '/v6', '2025-07-08 21:38:28.766814', NULL, NULL);
INSERT INTO public.ip_visits VALUES (25, '127.0.0.1', 'curl/8.7.1', NULL, '/v6', '2025-07-08 21:40:41.241441', NULL, NULL);
INSERT INTO public.ip_visits VALUES (26, '127.0.0.1', 'curl/8.7.1', NULL, '/', '2025-07-08 21:40:55.935191', NULL, NULL);
INSERT INTO public.ip_visits VALUES (27, '127.0.0.1', 'curl/8.7.1', NULL, '/v6', '2025-07-08 21:41:06.341969', NULL, NULL);
INSERT INTO public.ip_visits VALUES (28, '127.0.0.1', 'curl/8.7.1', NULL, '/v6', '2025-07-08 21:41:56.840731', NULL, NULL);
INSERT INTO public.ip_visits VALUES (29, '127.0.0.1', 'curl/8.7.1', NULL, '/v6', '2025-07-08 21:48:44.272291', NULL, NULL);
INSERT INTO public.ip_visits VALUES (30, '127.0.0.1', 'curl/8.7.1', NULL, '/', '2025-07-08 21:48:51.345989', NULL, NULL);
INSERT INTO public.ip_visits VALUES (31, '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', NULL, '/v6', '2025-07-08 21:49:22.424109', NULL, NULL);
INSERT INTO public.ip_visits VALUES (32, '127.0.0.1', 'curl/8.7.1', NULL, '/v6', '2025-07-08 21:59:16.407852', NULL, NULL);
INSERT INTO public.ip_visits VALUES (33, '127.0.0.1', 'curl/8.7.1', NULL, '/', '2025-07-08 21:59:22.860456', NULL, NULL);
INSERT INTO public.ip_visits VALUES (34, '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', NULL, '/v6', '2025-07-08 22:00:55.105338', NULL, NULL);
INSERT INTO public.ip_visits VALUES (35, '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', NULL, '/', '2025-07-08 22:01:42.525317', NULL, NULL);
INSERT INTO public.ip_visits VALUES (36, '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', NULL, '/v6', '2025-07-08 22:01:45.684973', NULL, NULL);
INSERT INTO public.ip_visits VALUES (37, '127.0.0.1', 'curl/8.7.1', NULL, '/v6', '2025-07-08 22:11:38.523592', NULL, NULL);
INSERT INTO public.ip_visits VALUES (38, '127.0.0.1', 'curl/8.7.1', NULL, '/', '2025-07-08 22:11:45.560566', NULL, NULL);
INSERT INTO public.ip_visits VALUES (39, '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', NULL, '/', '2025-07-08 22:14:07.40091', NULL, NULL);
INSERT INTO public.ip_visits VALUES (40, '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', NULL, '/v6', '2025-07-08 22:14:14.002938', NULL, NULL);
INSERT INTO public.ip_visits VALUES (41, '127.0.0.1', 'curl/8.7.1', NULL, '/v6', '2025-07-08 22:21:16.676558', NULL, NULL);
INSERT INTO public.ip_visits VALUES (42, '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', NULL, '/v6', '2025-07-08 22:32:46.502327', NULL, NULL);
INSERT INTO public.ip_visits VALUES (43, '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', 'http://127.0.0.1:5001/v6', '/assets/detail/20', '2025-07-08 22:33:36.506463', NULL, NULL);
INSERT INTO public.ip_visits VALUES (44, '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', NULL, '/', '2025-07-08 22:33:48.653832', NULL, NULL);
INSERT INTO public.ip_visits VALUES (45, '192.168.0.200', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', NULL, '/', '2025-07-08 22:33:53.22225', NULL, NULL);
INSERT INTO public.ip_visits VALUES (46, '192.168.0.200', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', NULL, '/v6', '2025-07-08 22:33:58.8911', NULL, NULL);
INSERT INTO public.ip_visits VALUES (47, '192.168.0.200', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36', NULL, '/', '2025-07-08 22:34:34.930778', NULL, NULL);


--
-- Data for Name: onchain_history; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--



--
-- Data for Name: platform_incomes; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

INSERT INTO public.platform_incomes VALUES (1, 2, 0.002875, '资产 2 交易手续费', 2, 4, 'mock_1741657622_Ev6fjJQR1p5rgWKQ8pH6Yu2tVSwLzQPp', '2025-03-11 01:47:04.884068');
INSERT INTO public.platform_incomes VALUES (2, 2, 0.002875, '资产 2 交易手续费', 2, 5, 'mock_1741657683_gv92RGSj2UWdDkLQzFFE3Qo9qmaZetKA', '2025-03-11 01:48:05.338805');
INSERT INTO public.platform_incomes VALUES (3, 2, 0.002875, '资产 2 交易手续费', 2, 6, 'mock_1741658983_ZADEqioxxGmLCTeP1r5mbf5KXzNiFH1z', '2025-03-11 02:09:45.153279');
INSERT INTO public.platform_incomes VALUES (4, 2, 0.014375, '交易佣金 - 资产ID2, 交易ID55', 2, 55, NULL, '2025-03-12 16:20:51.221679');
INSERT INTO public.platform_incomes VALUES (5, 2, 0.002875, '交易佣金 - 资产ID2, 交易ID56', 2, 56, NULL, '2025-03-12 16:33:34.110181');
INSERT INTO public.platform_incomes VALUES (6, 2, 0.00575, '交易佣金 - 资产ID2, 交易ID57', 2, 57, NULL, '2025-03-12 16:33:51.261738');
INSERT INTO public.platform_incomes VALUES (7, 2, 0.008625, '交易佣金 - 资产ID2, 交易ID58', 2, 58, NULL, '2025-03-12 16:33:59.779962');
INSERT INTO public.platform_incomes VALUES (8, 2, 0.0115, '交易佣金 - 资产ID2, 交易ID59', 2, 59, NULL, '2025-03-12 16:34:05.786409');
INSERT INTO public.platform_incomes VALUES (9, 2, 0.014375, '交易佣金 - 资产ID2, 交易ID60', 2, 60, NULL, '2025-03-12 16:34:13.226798');
INSERT INTO public.platform_incomes VALUES (10, 2, 0.01725, '交易佣金 - 资产ID2, 交易ID61', 2, 61, NULL, '2025-03-12 16:37:20.65675');
INSERT INTO public.platform_incomes VALUES (11, 2, 0.020125, '交易佣金 - 资产ID2, 交易ID62', 2, 62, NULL, '2025-03-12 16:37:36.105763');
INSERT INTO public.platform_incomes VALUES (12, 2, 0.002875, '交易佣金 - 资产ID2, 交易ID63', 2, 63, NULL, '2025-03-12 23:57:20.999575');
INSERT INTO public.platform_incomes VALUES (13, 2, 0.0115, '交易佣金 - 资产ID2, 交易ID64', 2, 64, NULL, '2025-03-12 23:57:55.820254');
INSERT INTO public.platform_incomes VALUES (14, 2, 0.014375, '交易佣金 - 资产ID2, 交易ID65', 2, 65, NULL, '2025-03-13 00:51:09.337645');
INSERT INTO public.platform_incomes VALUES (15, 2, 0.002875, '交易佣金 - 资产ID2, 交易ID66', 2, 66, NULL, '2025-03-13 06:04:03.157314');
INSERT INTO public.platform_incomes VALUES (16, 2, 0.00575, '交易佣金 - 资产ID2, 交易ID67', 2, 67, NULL, '2025-03-13 06:04:11.711211');
INSERT INTO public.platform_incomes VALUES (17, 2, 0.008625, '交易佣金 - 资产ID2, 交易ID68', 2, 68, NULL, '2025-03-13 06:17:39.147821');
INSERT INTO public.platform_incomes VALUES (18, 2, 0.002875, '交易佣金 - 资产ID2, 交易ID70', 2, 70, NULL, '2025-03-13 08:04:19.726716');
INSERT INTO public.platform_incomes VALUES (19, 2, 0.0115, '交易佣金 - 资产ID2, 交易ID71', 2, 71, NULL, '2025-03-13 08:15:46.748165');
INSERT INTO public.platform_incomes VALUES (20, 2, 0.008625, '交易佣金 - 资产ID2, 交易ID72', 2, 72, NULL, '2025-03-13 08:16:05.027347');
INSERT INTO public.platform_incomes VALUES (21, 2, 0.01725, '交易佣金 - 资产ID2, 交易ID73', 2, 73, NULL, '2025-03-13 08:18:16.622401');
INSERT INTO public.platform_incomes VALUES (22, 2, 0.002875, '交易佣金 - 资产ID2, 交易ID74', 2, 74, NULL, '2025-03-13 12:39:53.716111');
INSERT INTO public.platform_incomes VALUES (23, 2, 0.00575, '交易佣金 - 资产ID2, 交易ID75', 2, 75, NULL, '2025-03-13 12:40:51.888779');
INSERT INTO public.platform_incomes VALUES (24, 2, 0.008625, '交易佣金 - 资产ID2, 交易ID76', 2, 76, NULL, '2025-03-13 12:50:44.502709');
INSERT INTO public.platform_incomes VALUES (25, 2, 0.0115, '交易佣金 - 资产ID2, 交易ID77', 2, 77, NULL, '2025-03-13 12:51:18.893752');
INSERT INTO public.platform_incomes VALUES (26, 2, 0.014375, '交易佣金 - 资产ID2, 交易ID78', 2, 78, NULL, '2025-03-13 12:58:11.093298');
INSERT INTO public.platform_incomes VALUES (27, 2, 0.0115, '交易佣金 - 资产ID2, 交易ID79', 2, 79, NULL, '2025-03-13 13:04:09.428773');
INSERT INTO public.platform_incomes VALUES (28, 2, 0.008625, '交易佣金 - 资产ID2, 交易ID80', 2, 80, NULL, '2025-03-13 13:14:15.425583');
INSERT INTO public.platform_incomes VALUES (29, 2, 0.00575, '交易佣金 - 资产ID2, 交易ID81', 2, 81, NULL, '2025-03-13 13:42:57.616721');
INSERT INTO public.platform_incomes VALUES (30, 2, 0.002875, '交易佣金 - 资产ID2, 交易ID82', 2, 82, NULL, '2025-03-13 13:43:15.120151');
INSERT INTO public.platform_incomes VALUES (31, 2, 0.002875, '交易佣金 - 资产ID2, 交易ID83', 2, 83, NULL, '2025-03-13 14:22:14.420887');
INSERT INTO public.platform_incomes VALUES (32, 2, 0.002875, '交易佣金 - 资产ID2, 交易ID84', 2, 84, NULL, '2025-03-13 14:51:24.043172');
INSERT INTO public.platform_incomes VALUES (33, 2, 0.00575, '交易佣金 - 资产ID2, 交易ID85', 2, 85, NULL, '2025-03-13 14:51:40.136172');
INSERT INTO public.platform_incomes VALUES (34, 2, 0.002875, '交易佣金 - 资产ID2, 交易ID86', 2, 86, NULL, '2025-03-13 15:17:55.02148');
INSERT INTO public.platform_incomes VALUES (35, 2, 0.00575, '交易佣金 - 资产ID2, 交易ID87', 2, 87, NULL, '2025-03-13 15:47:42.406197');
INSERT INTO public.platform_incomes VALUES (36, 2, 0.02875, '交易佣金 - 资产ID2, 交易ID88', 2, 88, NULL, '2025-03-13 16:03:48.594235');
INSERT INTO public.platform_incomes VALUES (37, 2, 0.002875, '交易佣金 - 资产ID2, 交易ID89', 2, 89, NULL, '2025-03-16 16:03:36.418639');
INSERT INTO public.platform_incomes VALUES (38, 2, 0.020125, '交易佣金 - 资产ID2, 交易ID91', 2, 91, NULL, '2025-03-16 18:57:09.36247');
INSERT INTO public.platform_incomes VALUES (39, 2, 0.020125, '交易佣金 - 资产ID2, 交易ID92', 2, 92, NULL, '2025-03-16 19:10:44.321134');
INSERT INTO public.platform_incomes VALUES (40, 2, 0.04025, '交易佣金 - 资产ID2, 交易ID93', 2, 93, NULL, '2025-03-16 19:11:14.10692');


--
-- Data for Name: share_messages; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

INSERT INTO public.share_messages VALUES (4, '🚀 发现优质RWA资产！真实世界资产数字化投资新机遇，透明度高、收益稳定。通过我的专属链接投资，我们都能获得长期收益！', true, 3, '2025-05-30 21:17:45.90579', '2025-05-30 21:17:45.905792');
INSERT INTO public.share_messages VALUES (5, '💎 区块链遇见传统资产！这个RWA项目通过区块链技术让实体资产投资更加透明安全。一起探索数字化投资的未来吧！', true, 2, '2025-05-30 21:17:45.905792', '2025-05-30 21:17:45.905792');
INSERT INTO public.share_messages VALUES (6, '🌟 投资新趋势：真实世界资产代币化！房产、艺术品等实体资产现在可以通过区块链投资，门槛更低，流动性更强！', true, 2, '2025-05-30 21:17:45.905793', '2025-05-30 21:17:45.905794');
INSERT INTO public.share_messages VALUES (7, '🔗 RWA投资社区邀请！真实世界资产代币化让投资更加透明、便捷。通过专属链接加入，共享投资智慧！', true, 2, '2025-05-30 21:17:45.905794', '2025-05-30 21:17:45.905795');
INSERT INTO public.share_messages VALUES (8, '📊 传统投资的区块链革命！RWA（真实世界资产）让房产、商品等实体投资变得更加民主化。点击探索投资新世界！', true, 1, '2025-05-30 21:17:45.905795', '2025-05-30 21:17:45.905795');


--
-- Data for Name: short_links; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

INSERT INTO public.short_links VALUES (1, 'QNoop2', 'http://example.com/asset/123', '2025-03-17 06:24:30.090505', NULL, 0, '0x123456789abcdef');
INSERT INTO public.short_links VALUES (2, 'cF73ND', 'http://127.0.0.1:9000/assets/RH-109774?ref=0x6260c4a9e9f725a9c40bede853240d311e80e9ee', '2025-03-17 06:41:59.476325', '2026-03-17 06:41:59.474951', 0, '0x6260c4a9e9f725a9c40bede853240d311e80e9ee');
INSERT INTO public.short_links VALUES (3, 'FI8Hkp', 'http://127.0.0.1:9000/assets/RH-109774?ref=0x6260c4a9e9f725a9c40bede853240d311e80e9ee', '2025-03-17 06:42:45.180811', '2026-03-17 06:42:45.180151', 0, '0x6260c4a9e9f725a9c40bede853240d311e80e9ee');
INSERT INTO public.short_links VALUES (4, 'AyzZs2', 'http://127.0.0.1:9000/assets/RH-109774?ref=0x6260c4a9e9f725a9c40bede853240d311e80e9ee', '2025-03-17 06:49:16.536901', '2026-03-17 06:49:16.536498', 0, '0x6260c4a9e9f725a9c40bede853240d311e80e9ee');
INSERT INTO public.short_links VALUES (5, 'MGMJB8', 'http://127.0.0.1:8000/assets/RH-109774?ref=0x6260c4a9e9f725a9c40bede853240d311e80e9ee', '2025-03-17 06:50:41.510544', '2026-03-17 06:50:41.508588', 0, '0x6260c4a9e9f725a9c40bede853240d311e80e9ee');
INSERT INTO public.short_links VALUES (6, 'mlM6wr', 'http://127.0.0.1:8000/assets/RH-109774?ref=0x6260c4a9e9f725a9c40bede853240d311e80e9ee', '2025-03-17 06:50:50.030143', '2026-03-17 06:50:50.029468', 0, '0x6260c4a9e9f725a9c40bede853240d311e80e9ee');
INSERT INTO public.short_links VALUES (7, 'axlOxn', 'http://127.0.0.1:8000/assets/RH-109774?ref=0x6260c4a9e9f725a9c40bede853240d311e80e9ee', '2025-03-17 06:51:40.038977', '2026-03-17 06:51:40.037886', 0, '0x6260c4a9e9f725a9c40bede853240d311e80e9ee');
INSERT INTO public.short_links VALUES (8, 'C3aKHK', 'http://127.0.0.1:8000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-17 07:52:48.923576', '2026-03-17 07:52:48.922994', 0, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR');
INSERT INTO public.short_links VALUES (9, 'y5wkyo', 'http://127.0.0.1:8000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-17 07:52:54.051964', '2026-03-17 07:52:54.051158', 0, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR');
INSERT INTO public.short_links VALUES (10, 'SABXp0', 'http://127.0.0.1:8000/assets/RH-109774?ref=0x6260c4a9e9f725a9c40bede853240d311e80e9ee', '2025-03-17 07:54:21.918511', '2026-03-17 07:54:21.91803', 0, '0x6260c4a9e9f725a9c40bede853240d311e80e9ee');
INSERT INTO public.short_links VALUES (11, 'zEtAAm', 'http://127.0.0.1:8000/assets/RH-109774?ref=0x6260c4a9e9f725a9c40bede853240d311e80e9ee', '2025-03-17 08:59:48.230934', '2026-03-17 08:59:48.230006', 0, '0x6260c4a9e9f725a9c40bede853240d311e80e9ee');
INSERT INTO public.short_links VALUES (12, 'zRZKBv', 'http://127.0.0.1:5000/assets/RH-109774?ref=0x6260c4a9e9f725a9c40bede853240d311e80e9ee', '2025-03-17 12:23:26.605907', '2026-03-17 12:23:26.603108', 0, '0x6260c4a9e9f725a9c40bede853240d311e80e9ee');
INSERT INTO public.short_links VALUES (13, 'jjOsAr', 'http://127.0.0.1:5000/assets/RH-109774?ref=0x6260c4a9e9f725a9c40bede853240d311e80e9ee', '2025-03-17 12:55:03.505241', '2026-03-17 12:55:03.503144', 0, '0x6260c4a9e9f725a9c40bede853240d311e80e9ee');
INSERT INTO public.short_links VALUES (14, 'aeQncd', 'http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-17 13:17:00.323135', '2026-03-17 13:17:00.322322', 0, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR');
INSERT INTO public.short_links VALUES (15, 'g8NTTP', 'http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-17 13:17:07.535723', '2026-03-17 13:17:07.535252', 0, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR');
INSERT INTO public.short_links VALUES (16, 'rHSfCW', 'http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-17 13:17:43.461365', '2026-03-17 13:17:43.460505', 0, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR');
INSERT INTO public.short_links VALUES (17, 'e1tBV3', 'http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-17 13:18:07.116898', '2026-03-17 13:18:07.111747', 0, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR');
INSERT INTO public.short_links VALUES (18, 'g3NUJw', 'http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-17 13:18:09.80652', '2026-03-17 13:18:09.806026', 0, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR');
INSERT INTO public.short_links VALUES (19, 'IzBEQo', 'http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-17 13:18:15.27811', '2026-03-17 13:18:15.277587', 0, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR');
INSERT INTO public.short_links VALUES (20, 'tkjDy2', 'http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-17 13:18:26.72366', '2026-03-17 13:18:26.722978', 0, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR');
INSERT INTO public.short_links VALUES (21, '4xZT3r', 'http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-17 13:18:31.848799', '2026-03-17 13:18:31.848298', 0, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR');
INSERT INTO public.short_links VALUES (22, 'vpnBlK', 'http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-17 13:18:36.794353', '2026-03-17 13:18:36.793878', 0, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR');
INSERT INTO public.short_links VALUES (23, 'BA8hqE', 'http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-17 13:18:40.626197', '2026-03-17 13:18:40.624863', 0, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR');
INSERT INTO public.short_links VALUES (24, 'NCf8wF', 'http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-17 13:18:44.294044', '2026-03-17 13:18:44.293567', 0, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR');
INSERT INTO public.short_links VALUES (25, 'qn1OuI', 'http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-17 13:18:49.986129', '2026-03-17 13:18:49.98318', 0, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR');
INSERT INTO public.short_links VALUES (26, 'Ql6BC1', 'http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-17 13:18:52.385786', '2026-03-17 13:18:52.385284', 0, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR');
INSERT INTO public.short_links VALUES (27, 'ZX2NXg', 'http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-17 13:18:55.78561', '2026-03-17 13:18:55.78526', 0, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR');
INSERT INTO public.short_links VALUES (28, 'tVS5vm', 'http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-17 13:18:59.490261', '2026-03-17 13:18:59.489907', 0, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR');
INSERT INTO public.short_links VALUES (29, 'QhqU9g', 'http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-17 13:19:01.156524', '2026-03-17 13:19:01.156116', 0, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR');
INSERT INTO public.short_links VALUES (30, 'qZWU1A', 'http://127.0.0.1:5000/assets/RH-109774?ref=0x6260c4a9e9f725a9c40bede853240d311e80e9ee', '2025-03-17 13:25:23.433814', '2026-03-17 13:25:23.433328', 0, '0x6260c4a9e9f725a9c40bede853240d311e80e9ee');
INSERT INTO public.short_links VALUES (31, 'eh2gS5', 'http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-17 13:25:29.647967', '2026-03-17 13:25:29.647577', 0, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR');
INSERT INTO public.short_links VALUES (32, 'Jf8pSW', 'http://127.0.0.1:5000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-17 13:25:36.355665', '2026-03-17 13:25:36.355486', 0, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR');
INSERT INTO public.short_links VALUES (33, 'Vjjk2p', 'http://127.0.0.1:9000/assets/RH-109774?ref=0xfe2b20231530e533552c5573582d6705b3ee9a1d', '2025-03-17 13:28:09.786118', '2026-03-17 13:28:09.779529', 0, '0xfe2b20231530e533552c5573582d6705b3ee9a1d');
INSERT INTO public.short_links VALUES (34, '1raWnn', 'http://127.0.0.1:9000/assets/RH-109774?ref=0xfe2b20231530e533552c5573582d6705b3ee9a1d', '2025-03-17 13:28:25.15073', '2026-03-17 13:28:25.150071', 0, '0xfe2b20231530e533552c5573582d6705b3ee9a1d');
INSERT INTO public.short_links VALUES (35, 'Hxye3I', 'http://127.0.0.1:8000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-17 13:38:58.160239', '2026-03-17 13:38:58.158204', 0, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR');
INSERT INTO public.short_links VALUES (36, 'n7SfZh', 'http://127.0.0.1:8000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-17 13:43:40.535806', '2026-03-17 13:43:40.535162', 0, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR');
INSERT INTO public.short_links VALUES (37, 'SuCBql', 'http://127.0.0.1:8000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-17 13:44:28.836188', '2026-03-17 13:44:28.835686', 0, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR');
INSERT INTO public.short_links VALUES (38, 'UNS00i', 'http://127.0.0.1:8000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-17 13:44:55.242824', '2026-03-17 13:44:55.241473', 0, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR');
INSERT INTO public.short_links VALUES (39, 'ig1ucf', 'http://127.0.0.1:8000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-17 14:43:09.82465', '2026-03-17 14:43:09.823885', 0, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR');
INSERT INTO public.short_links VALUES (40, 'VxcS9c', 'http://127.0.0.1:8000/assets/RH-109774?ref=0x6260c4a9e9f725a9c40bede853240d311e80e9ee', '2025-03-17 15:32:08.32396', '2026-03-17 15:32:08.319996', 0, '0x6260c4a9e9f725a9c40bede853240d311e80e9ee');
INSERT INTO public.short_links VALUES (41, '8Fy9Xa', 'http://127.0.0.1:8000/assets/RH-109774?ref=0x6260c4a9e9f725a9c40bede853240d311e80e9ee', '2025-03-17 15:32:34.967009', '2026-03-17 15:32:34.966412', 0, '0x6260c4a9e9f725a9c40bede853240d311e80e9ee');
INSERT INTO public.short_links VALUES (42, '6eHJzU', 'http://127.0.0.1:8000/assets/RH-109774?ref=0x6260c4a9e9f725a9c40bede853240d311e80e9ee', '2025-03-17 15:32:38.595202', '2026-03-17 15:32:38.594663', 0, '0x6260c4a9e9f725a9c40bede853240d311e80e9ee');
INSERT INTO public.short_links VALUES (43, '9CT1By', 'http://127.0.0.1:8000/assets/RH-109774?ref=0x6260c4a9e9f725a9c40bede853240d311e80e9ee', '2025-03-17 16:05:19.425427', '2026-03-17 16:05:19.424937', 0, '0x6260c4a9e9f725a9c40bede853240d311e80e9ee');
INSERT INTO public.short_links VALUES (44, 'MGksHt', 'http://127.0.0.1:8000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-17 17:21:48.885438', '2026-03-17 17:21:48.884615', 0, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR');
INSERT INTO public.short_links VALUES (45, 'xHPVtO', 'http://127.0.0.1:8000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-18 10:01:07.162402', '2026-03-18 10:01:07.160722', 0, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR');
INSERT INTO public.short_links VALUES (46, 'NO75rL', 'http://127.0.0.1:8000/assets/10?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-18 13:52:00.477426', '2026-03-18 13:52:00.476493', 0, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR');
INSERT INTO public.short_links VALUES (47, 'R4eBON', 'http://127.0.0.1:8000/assets/10?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-18 14:41:32.943737', '2026-03-18 14:41:32.94204', 0, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR');
INSERT INTO public.short_links VALUES (48, 'lfiylC', 'http://127.0.0.1:8000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-18 17:33:43.104652', '2026-03-18 17:33:43.102782', 0, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR');
INSERT INTO public.short_links VALUES (49, 'yAmXTJ', 'http://127.0.0.1:8000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-18 18:58:50.935444', '2026-03-18 18:58:50.93441', 0, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR');
INSERT INTO public.short_links VALUES (50, 'x0olqD', 'http://127.0.0.1:8000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-19 06:47:27.956059', '2026-03-19 06:47:27.953377', 0, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR');
INSERT INTO public.short_links VALUES (51, 'RE6Kd9', 'http://127.0.0.1:8000/assets/RH-109774?ref=EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR', '2025-03-19 06:49:22.379527', '2026-03-19 06:49:22.378969', 0, 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR');
INSERT INTO public.short_links VALUES (52, 'Y6yONO', 'http://127.0.0.1:8000/assets/RH-101719?ref=0x6394993426DBA3b654eF0052698Fe9E0B6A98870', '2025-03-19 10:50:40.19337', '2026-03-19 10:50:40.191664', 0, '0x6394993426DBA3b654eF0052698Fe9E0B6A98870');
INSERT INTO public.short_links VALUES (53, 'CFnJ5y', 'https://example.com', '2025-05-30 21:08:40.188464', '2026-05-30 21:08:40.188185', 0, NULL);


--
-- Data for Name: system_configs; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

INSERT INTO public.system_configs VALUES (1, 'PLATFORM_FEE_ADDRESS', 'EsfAFJFBa49RMc2UZNUjsWhGFZeA1uLgEkNPY5oYsDW4', 'Platform fee collection address', '2025-05-26 09:05:46.150915', '2025-05-26 09:05:46.150916');
INSERT INTO public.system_configs VALUES (2, 'ASSET_CREATION_FEE_ADDRESS', 'EsfAFJFBa49RMc2UZNUjsWhGFZeA1uLgEkNPY5oYsDW4', 'Asset creation fee collection address', '2025-05-26 09:05:46.157009', '2025-05-26 09:05:46.157011');
INSERT INTO public.system_configs VALUES (3, 'ASSET_CREATION_FEE_AMOUNT', '0.02', 'Asset creation fee amount in USDC', '2025-05-26 09:05:46.158027', '2025-05-26 09:05:46.158028');
INSERT INTO public.system_configs VALUES (4, 'PLATFORM_FEE_BASIS_POINTS', '350', 'Platform fee in basis points (350 = 3.5%)', '2025-05-26 09:05:46.158908', '2025-05-26 09:05:46.158909');
INSERT INTO public.system_configs VALUES (5, 'SOLANA_WALLET_ADDRESS', '6UrwhN2rqQvo2tBfc9FZCdUbt9JLs3BJiEm7pv4NM41b', '新的安全钱包地址', '2025-05-27 06:39:28.015536', '2025-05-27 06:39:28.015537');


--
-- Data for Name: transactions; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--



--
-- Data for Name: user_commission_balance; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--

INSERT INTO public.user_commission_balance VALUES (2, '0x1234567890123456789012345678901234567890', 301.50000000, 201.00000000, 0.00000000, 100.50000000, 'USDC', '2025-05-26 16:14:14.602921', '2025-05-26 16:10:52.159178');
INSERT INTO public.user_commission_balance VALUES (3, '0xtest123456789012345678901234567890', 150.00000000, 60.00000000, 30.00000000, 60.00000000, 'USDC', '2025-05-26 16:14:14.749053', '2025-05-26 16:10:52.307403');


--
-- Data for Name: user_referrals; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--



--
-- Data for Name: withdrawal_requests; Type: TABLE DATA; Schema: public; Owner: rwa_hub_user
--



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
-- PostgreSQL database dump complete
--

