import 'alova';

/**
 * 接口请求message提示方式
 */
export type MessageType = 'message' | 'modal' | 'none' | 'notification';

/**
 * 拓展自己的Meta
 */
// eslint-disable-next-line @typescript-eslint/no-empty-object-type
export type AlovaMeta = {};

declare module 'alova' {
  export interface AlovaCustomTypes {
    meta: AlovaMeta;
  }
}

/**
 * 拓展axios的请求配置
 */
declare module 'axios' {
  interface AxiosRequestConfig {
    /**
     * 是否需要对请求体进行加密
     */
    encrypt?: boolean;
    /**
     * 错误弹窗类型
     */
    errorMessageMode?: MessageType;
    /**
     * 是否返回原生axios响应
     */
    isReturnNativeResponse?: boolean;
    /**
     * 是否需要转换响应 即只获取{code, msg, data}中的data
     */
    isTransformResponse?: boolean;
    /**
     * 接口请求成功时的提示方式
     */
    successMessageMode?: MessageType;
    /**
     * 是否需要在请求头中添加 token
     */
    withToken?: boolean;
  }
}

export {};
