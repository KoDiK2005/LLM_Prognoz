export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-zinc-50 px-6 text-center dark:bg-black">
      <h1 className="text-3xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
        LLM Prognoz
      </h1>
      <p className="mt-4 max-w-md text-lg text-zinc-600 dark:text-zinc-400">
        SaaS-платформа для прогнозов по вашим данным: статистическая модель
        считает цифры, а несколько LLM объясняют и сравнивают результат.
      </p>
    </div>
  );
}
