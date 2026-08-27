package com.walnut.seed.common.core.domain;

import com.walnut.seed.common.core.constant.HttpStatus;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serial;
import java.io.Serializable;
import java.util.List;

/**
 * 响应信息主体
 *
 * @author deepin_sir
 */
@Data
@NoArgsConstructor
public class ApiResponse<T> implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    /**
     * 成功
     */
    public static final int SUCCESS = 200;

    /**
     * 失败
     */
    public static final int FAIL = 500;

    private int code;

    private String msg;

    private T data;



    public static <T> ApiResponse<T> ok() {
        return restResult(null, SUCCESS, "操作成功");
    }

    public static <T> ApiResponse<T> ok(T data) {
        return restResult(data, SUCCESS, "操作成功");
    }

    public static <T> ApiResponse<T> ok(String msg) {
        return restResult(null, SUCCESS, msg);
    }

    public static <T> ApiResponse<T> ok(String msg, T data) {
        return restResult(data, SUCCESS, msg);
    }

    public static <T> ApiResponse<T> fail() {
        return restResult(null, FAIL, "操作失败");
    }

    public static <T> ApiResponse<T> fail(String msg) {
        return restResult(null, FAIL, msg);
    }

    public static <T> ApiResponse<T> fail(T data) {
        return restResult(data, FAIL, "操作失败");
    }

    public static <T> ApiResponse<T> fail(String msg, T data) {
        return restResult(data, FAIL, msg);
    }

    public static <T> ApiResponse<T> fail(int code, String msg) {
        return restResult(null, code, msg);
    }

    /**
     * 返回警告消息
     *
     * @param msg 返回内容
     * @return 警告消息
     */
    public static <T> ApiResponse<T> warn(String msg) {
        return restResult(null, HttpStatus.WARN, msg);
    }

    /**
     * 返回警告消息
     *
     * @param msg  返回内容
     * @param data 数据对象
     * @return 警告消息
     */
    public static <T> ApiResponse<T> warn(String msg, T data) {
        return restResult(data, HttpStatus.WARN, msg);
    }

    /**
     * 分页响应 — rows/total 在顶层，与前端 ...other rest-spread 兼容
     *
     * @return 分页响应
     */

    private static <T> ApiResponse<T> restResult(T data, int code, String msg) {
        ApiResponse<T> r = new ApiResponse<>();
        r.setCode(code);
        r.setData(data);
        r.setMsg(msg);
        return r;
    }

    public static <T> Boolean isError(ApiResponse<T> ret) {
        return !isSuccess(ret);
    }

    public static <T> Boolean isSuccess(ApiResponse<T> ret) {
        return ApiResponse.SUCCESS == ret.getCode();
    }
}
