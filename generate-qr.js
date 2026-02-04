#!/usr/bin/env node

import { startWebLoginWithQr } from '/root/dist/web/login-qr.js';
import { writeFileSync } from 'fs';

async function main() {
    console.log('Starting WhatsApp login...');

    try {
        const result = await startWebLoginWithQr({
            timeoutMs: 120000 // 2分钟超时
        });

        if (result.qrDataUrl) {
            // 提取base64数据
            const base64Data = result.qrDataUrl.replace(/^data:image\/png;base64,/, '');
            const buffer = Buffer.from(base64Data, 'base64');

            // 保存文件
            const qrPath = '/root/.openclaw/workspace/whatsapp-qr.png';
            writeFileSync(qrPath, buffer);

            console.log('\n✅ QR码已生成！');
            console.log(`📁 文件路径: ${qrPath}`);
            console.log('\n请在MAC上运行以下命令下载QR码图片：');
            console.log(`  scp root@${process.env.SSH_CONNECTION?.split(' ')[0]}:${qrPath} ~/Desktop/whatsapp-qr.png`);
            console.log('\n然后用手机扫描~/Desktop/whatsapp-qr.png文件');
        } else if (result.message) {
            console.log('\n' + result.message);
        }
    } catch (error) {
        console.error('Error:', error.message);
        process.exit(1);
    }
}

main();
