import { decode } from 'base64-arraybuffer';

// On the server, we're using jupyter_client.session.json_packer to serialize messages,
// and it encodes binary data (i.e., buffers) as base64, so decode it before passing it
// along to the comm logic
export function jsonParse(x: string) {
  const msg = JSON.parse(x);
  msg.buffers = msg.buffers.map((b: any) => decode(b));
  return msg;
}