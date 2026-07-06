/// <reference types="vite/client" />

declare module "*.c?raw" {
  const content: string;
  export default content;
}
