FROM node:22-alpine
WORKDIR /app
RUN chown node:node /app
USER node
COPY --chown=node:node package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY --chown=node:node . .
ARG NEXT_PUBLIC_GUESTLIFT_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_GUESTLIFT_API_URL=$NEXT_PUBLIC_GUESTLIFT_API_URL
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "start"]
