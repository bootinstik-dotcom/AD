FROM denoland/deno:2.2.12
WORKDIR /app
COPY telegram-webhook.ts ./telegram-webhook.ts
RUN deno cache telegram-webhook.ts
EXPOSE 8000
CMD ["run", "--cached-only", "--allow-net", "--allow-env", "telegram-webhook.ts"]
