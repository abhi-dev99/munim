-- Munim.ai — HSN GST Rate Fix Migration
-- Run this in Supabase SQL Editor for instant bulk update
-- Applies official GST chapter rates to all 21,934 HSN codes

-- Step 1: Update by chapter (first 2 digits of HSN code)
UPDATE hsn_codes SET gst_rate = 0.0  WHERE SUBSTRING(hsn_code, 1, 2) IN ('01','02','05','07','08','09','10','11','12','13','14','23','26');
UPDATE hsn_codes SET gst_rate = 5.0  WHERE SUBSTRING(hsn_code, 1, 2) IN ('03','04','06','15','17','25','27','31','41','50','51','52','53','54','55','60','61','62','63','89');
UPDATE hsn_codes SET gst_rate = 12.0 WHERE SUBSTRING(hsn_code, 1, 2) IN ('16','20','21','30','44','45','46','47','49','56','57','58','59','86','87','93','97');
UPDATE hsn_codes SET gst_rate = 18.0 WHERE SUBSTRING(hsn_code, 1, 2) IN ('18','19','22','28','29','32','33','34','35','36','37','38','39','40','42','43','48','64','65','66','67','68','69','70','72','73','74','75','76','77','78','79','80','81','82','83','84','85','88','90','91','94','95','96','99');
UPDATE hsn_codes SET gst_rate = 28.0 WHERE SUBSTRING(hsn_code, 1, 2) IN ('24','92');
UPDATE hsn_codes SET gst_rate = 3.0  WHERE SUBSTRING(hsn_code, 1, 2) = '71';

-- Step 2: Specific 4-digit overrides (take priority over chapter defaults)
-- Motor vehicles
UPDATE hsn_codes SET gst_rate = 28.0 WHERE hsn_code LIKE '8703%' OR hsn_code LIKE '8704%' OR hsn_code LIKE '8711%';
-- Cement
UPDATE hsn_codes SET gst_rate = 28.0 WHERE hsn_code LIKE '2523%';
-- Air conditioners, refrigerators, washing machines
UPDATE hsn_codes SET gst_rate = 28.0 WHERE hsn_code LIKE '8415%' OR hsn_code LIKE '8418%' OR hsn_code LIKE '8450%';
-- Mobile phones
UPDATE hsn_codes SET gst_rate = 12.0 WHERE hsn_code LIKE '8517%';
-- Solar panels
UPDATE hsn_codes SET gst_rate = 12.0 WHERE hsn_code LIKE '8541%';
-- Medicines / Pharma
UPDATE hsn_codes SET gst_rate = 5.0  WHERE hsn_code LIKE '3004%' OR hsn_code LIKE '3003%' OR hsn_code LIKE '3002%';
-- Fertilizers
UPDATE hsn_codes SET gst_rate = 5.0  WHERE hsn_code LIKE '3101%' OR hsn_code LIKE '3102%' OR hsn_code LIKE '3103%';
-- Gold
UPDATE hsn_codes SET gst_rate = 3.0  WHERE hsn_code LIKE '7108%' OR hsn_code LIKE '7107%';
-- Petroleum (exempt)
UPDATE hsn_codes SET gst_rate = 0.0  WHERE hsn_code LIKE '2709%' OR hsn_code LIKE '2710%';
-- Books, Newspapers
UPDATE hsn_codes SET gst_rate = 0.0  WHERE hsn_code LIKE '4901%' OR hsn_code LIKE '4902%' OR hsn_code LIKE '4903%';
-- Tobacco
UPDATE hsn_codes SET gst_rate = 28.0 WHERE hsn_code LIKE '2401%' OR hsn_code LIKE '2402%' OR hsn_code LIKE '2403%';
-- Coal
UPDATE hsn_codes SET gst_rate = 5.0  WHERE hsn_code LIKE '2701%' OR hsn_code LIKE '2702%';
-- LPG / Natural gas
UPDATE hsn_codes SET gst_rate = 5.0  WHERE hsn_code LIKE '2711%';
-- Iron ore
UPDATE hsn_codes SET gst_rate = 5.0  WHERE hsn_code LIKE '2601%';
-- Cotton yarn
UPDATE hsn_codes SET gst_rate = 5.0  WHERE hsn_code LIKE '5205%' OR hsn_code LIKE '5206%';
-- Railway
UPDATE hsn_codes SET gst_rate = 5.0  WHERE hsn_code LIKE '8601%' OR hsn_code LIKE '8602%' OR hsn_code LIKE '8603%';

-- Step 3: SAC (Service) codes starting with 99
UPDATE hsn_codes SET gst_rate = 18.0 WHERE hsn_code LIKE '9954%';
UPDATE hsn_codes SET gst_rate = 18.0 WHERE hsn_code LIKE '9963%';
UPDATE hsn_codes SET gst_rate = 18.0 WHERE hsn_code LIKE '9964%';
UPDATE hsn_codes SET gst_rate = 18.0 WHERE hsn_code LIKE '9965%';
UPDATE hsn_codes SET gst_rate = 18.0 WHERE hsn_code LIKE '9971%';
UPDATE hsn_codes SET gst_rate = 18.0 WHERE hsn_code LIKE '9972%';
UPDATE hsn_codes SET gst_rate = 18.0 WHERE hsn_code LIKE '9973%';
UPDATE hsn_codes SET gst_rate = 18.0 WHERE hsn_code LIKE '9983%';
UPDATE hsn_codes SET gst_rate = 18.0 WHERE hsn_code LIKE '9984%';
UPDATE hsn_codes SET gst_rate = 18.0 WHERE hsn_code LIKE '9985%';
UPDATE hsn_codes SET gst_rate = 0.0  WHERE hsn_code LIKE '9986%';
UPDATE hsn_codes SET gst_rate = 18.0 WHERE hsn_code LIKE '9987%';
UPDATE hsn_codes SET gst_rate = 5.0  WHERE hsn_code LIKE '9988%';
UPDATE hsn_codes SET gst_rate = 0.0  WHERE hsn_code LIKE '9991%';
UPDATE hsn_codes SET gst_rate = 0.0  WHERE hsn_code LIKE '9992%';
UPDATE hsn_codes SET gst_rate = 5.0  WHERE hsn_code LIKE '9993%';
UPDATE hsn_codes SET gst_rate = 18.0 WHERE hsn_code LIKE '9995%';
UPDATE hsn_codes SET gst_rate = 28.0 WHERE hsn_code LIKE '9996%';
UPDATE hsn_codes SET gst_rate = 18.0 WHERE hsn_code LIKE '9997%';

-- Verify
SELECT gst_rate, COUNT(*) as count FROM hsn_codes GROUP BY gst_rate ORDER BY gst_rate;
