const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });
require('dotenv').config({ path: path.join(__dirname, '.env') });

console.log('VOICE_PROVIDER:', process.env.VOICE_PROVIDER);
console.log('Qwen3_SPACE_URL:', process.env.Qwen3_SPACE_URL);
console.log('HF_API_TOKEN exists:', !!process.env.HF_API_TOKEN);
console.log('HF_API_TOKEN length:', process.env.HF_API_TOKEN ? process.env.HF_API_TOKEN.length : 0);
