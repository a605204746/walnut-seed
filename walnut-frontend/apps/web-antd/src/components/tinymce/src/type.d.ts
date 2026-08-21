export interface TinymceProps {
  height?: number | string;
  options?: Partial<InitOptions>;
  plugins?: string;
  toolbar?: string;
  disabled?: boolean;
}
